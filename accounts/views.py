from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from .forms import RegisterForm, AddressForm
from products.models import (
    Product,
    ProductVariant,
    ProductImage,
    Category,
    Offer,
)
from products.forms import (
    CategoryForm,
    ProductForm,
    ProductVariantForm,
    PriceHistoryForm,
    OfferForm,
)
from cart.models import Cart, CartItem
from wishlist.models import Wishlist, WishlistItem


def admin_table_context(
    request,
    queryset,
    search_fields,
    sort_options,
    default_sort,
    extra_query_params=None,
    low_stock_filter=False
):
    search_term = request.GET.get('q', '').strip()
    if search_term:
        search_query = Q()
        for field in search_fields:
            search_query |= Q(**{f'{field}__icontains': search_term})
        queryset = queryset.filter(search_query)

    sort_fields = {key: field for key, _label, field in sort_options}
    selected_sort = request.GET.get('sort', default_sort)
    if selected_sort not in sort_fields:
        selected_sort = default_sort

    direction = request.GET.get('direction', 'asc')
    if direction not in ('asc', 'desc'):
        direction = 'asc'

    ordering_fields = sort_fields[selected_sort]
    if isinstance(ordering_fields, str):
        ordering_fields = (ordering_fields,)
    ordering = [
        f'-{field}' if direction == 'desc' else field
        for field in ordering_fields
    ]
    queryset = queryset.order_by(*ordering)

    try:
        page_size = int(request.GET.get('per_page', 10))
    except (TypeError, ValueError):
        page_size = 10
    if page_size not in (10, 25, 50):
        page_size = 10

    page_obj = Paginator(queryset, page_size).get_page(request.GET.get('page'))
    return {
        'page_obj': page_obj,
        'table_search': search_term,
        'table_sort': selected_sort,
        'table_direction': direction,
        'table_page_size': page_size,
        'table_page_sizes': (10, 25, 50),
        'table_sort_options': sort_options,
        'table_extra_query_params': extra_query_params or {},
        'table_low_stock_filter': low_stock_filter,
    }


@login_required
def admin_dashboard(request):

    if not request.user.is_superuser:
        return redirect('home')

    from products.models import Product, Category
    from orders.models import Order, OrderItem, ReturnRequest
    from .models import User

    product_count = Product.objects.count()

    category_count = Category.objects.count()

    order_count = Order.objects.count()
    pending_return_count = ReturnRequest.objects.filter(status='pending').count()

    delivered_without_completed_return = (
        Q(orderitem__order__status='Delivered')
        & (
            Q(orderitem__order__return_request__isnull=True)
            | ~Q(orderitem__order__return_request__status='completed')
        )
    )
    inventory_now = timezone.now()
    current_offers = Offer.objects.filter(
        is_active=True,
        start_date__lte=inventory_now,
        end_date__gte=inventory_now
    ).order_by('variant_id', '-start_date')
    offer_by_variant = {}
    for offer in current_offers:
        offer_by_variant.setdefault(offer.variant_id, offer)

    inventory_queryset = (
        ProductVariant.objects.select_related('product', 'product__category')
        .annotate(
            sold_quantity=Coalesce(
                Sum(
                    'orderitem__quantity',
                    filter=delivered_without_completed_return
                ),
                Value(0),
                output_field=IntegerField()
            ),
            pending_quantity=Coalesce(
                Sum(
                    'orderitem__quantity',
                    filter=Q(
                        orderitem__stock_reserved=True,
                        orderitem__stock_restored=False,
                        orderitem__order__status__in=[
                            'Pending', 'Confirmed', 'Shipped'
                        ]
                    )
                ),
                Value(0),
                output_field=IntegerField()
            ),
        )
    )

    inventory_summary_data = ProductVariant.objects.aggregate(
        available_units=Coalesce(Sum('stock'), Value(0), output_field=IntegerField())
    )
    inventory_summary_data['sold_units'] = OrderItem.objects.filter(
        order__status='Delivered',
        stock_reserved=True,
        stock_restored=False,
        variant__isnull=False
    ).aggregate(total=Coalesce(Sum('quantity'), Value(0), output_field=IntegerField()))['total']
    inventory_summary_data['pending_units'] = OrderItem.objects.filter(
        order__status__in=['Pending', 'Confirmed', 'Shipped'],
        stock_reserved=True,
        stock_restored=False,
        variant__isnull=False
    ).aggregate(total=Coalesce(Sum('quantity'), Value(0), output_field=IntegerField()))['total']
    inventory_summary_data['low_stock_variants'] = ProductVariant.objects.filter(stock__lte=5).count()

    inventory_low_stock_only = request.GET.get('low_stock') == '1'
    if inventory_low_stock_only:
        inventory_queryset = inventory_queryset.filter(stock__lte=5)

    inventory_table_context = admin_table_context(
        request,
        inventory_queryset,
        ['product__name', 'product__category__name', 'color', 'size'],
        [
            ('name', 'Product name', ('product__name', 'color', 'size')),
            ('category', 'Category', 'product__category__name'),
            ('stock', 'Available stock', 'stock'),
            ('pending', 'Pending quantity', 'pending_quantity'),
            ('sold', 'Sold quantity', 'sold_quantity'),
            ('price', 'Base price', 'price'),
        ],
        'stock',
        extra_query_params={'low_stock': '1'} if inventory_low_stock_only else {},
        low_stock_filter=True
    )
    inventory_variants = list(inventory_table_context['page_obj'].object_list)
    for variant in inventory_variants:
        variant.is_low_stock = variant.stock <= 5
        variant.dashboard_offer = offer_by_variant.get(variant.pk)

    inventory_summary = inventory_summary_data

    current_month = timezone.localtime().replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )
    chart_months = []
    for month_offset in range(5, -1, -1):
        month_index = current_month.year * 12 + current_month.month - 1 - month_offset
        year, zero_based_month = divmod(month_index, 12)
        chart_months.append(
            current_month.replace(year=year, month=zero_based_month + 1)
        )

    monthly_rows = (
        Order.objects
        .filter(created_at__gte=chart_months[0])
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(order_total=Count('id'), revenue_total=Sum('total_amount'))
    )
    monthly_data = {
        row['month'].date().replace(day=1): row
        for row in monthly_rows
    }
    monthly_chart_data = {
        'labels': [month.strftime('%b %Y') for month in chart_months],
        'orders': [
            monthly_data.get(month.date(), {}).get('order_total', 0)
            for month in chart_months
        ],
        'revenue': [
            float(monthly_data.get(month.date(), {}).get('revenue_total') or 0)
            for month in chart_months
        ],
    }

    order_status_counts = dict(
        Order.objects.values_list('status')
        .annotate(status_total=Count('id'))
    )
    status_chart_data = {
        'labels': [label for _, label in Order.STATUS_CHOICES],
        'values': [
            order_status_counts.get(value, 0)
            for value, _ in Order.STATUS_CHOICES
        ],
    }

    user_count = User.objects.filter(
        is_superuser=False
    ).count()

    return render(
        request,
        'admin_dashboard/admin_dashboard.html',
        {
            'product_count': product_count,
            'category_count': category_count,
            'order_count': order_count,
            'pending_return_count': pending_return_count,
            'user_count': user_count,
            'monthly_chart_data': monthly_chart_data,
            'status_chart_data': status_chart_data,
            'inventory_variants': inventory_variants,
            'inventory_summary': inventory_summary,
            **inventory_table_context,
        }
    )


@login_required
@transaction.atomic
def restock_variant(request, variant_id):
    if not request.user.is_superuser:
        return redirect('home')

    if request.method != 'POST':
        return redirect('admin_dashboard')

    try:
        quantity = int(request.POST.get('quantity', ''))
    except (TypeError, ValueError):
        messages.error(request, 'Enter a valid number of units to add.')
        return redirect('admin_dashboard')

    if quantity <= 0:
        messages.error(request, 'Stock quantity must be greater than zero.')
        return redirect('admin_dashboard')

    variant = get_object_or_404(
        ProductVariant.objects.select_for_update().select_related('product'),
        pk=variant_id
    )
    ProductVariant.objects.filter(pk=variant.pk).update(
        stock=F('stock') + quantity
    )
    messages.success(
        request,
        f'Added {quantity} unit(s) to {variant.product.name} stock.'
    )
    return redirect('admin_dashboard')



@login_required
def admin_products(request):


    if not request.user.is_superuser:
        return redirect('home')

    products = Product.objects.select_related('category').annotate(
        variant_count=Count('variants', distinct=True),
        total_stock=Coalesce(
            Sum('variants__stock'),
            Value(0),
            output_field=IntegerField()
        )
    )
    table_context = admin_table_context(
        request,
        products,
        ['name', 'category__name', 'fabric'],
        [
            ('name', 'Product name', 'name'),
            ('category', 'Category', 'category__name'),
            ('stock', 'Total stock', 'total_stock'),
            ('created', 'Created', 'created_at'),
        ],
        'name'
    )

    return render(
        request,
    'admin_dashboard/products.html',
        {'products': table_context['page_obj'], **table_context}
)



@login_required
@transaction.atomic
def add_product(request):

    if not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':

        product_form = ProductForm(request.POST)

        if product_form.is_valid():

            # Get the category name typed/selected by admin
            category_name = product_form.cleaned_data.get('category')

            # Find existing category or create a new one
            category, created = Category.objects.get_or_create(
                name=category_name
            )

            # Save product without saving category text directly
            product = product_form.save(commit=False)

            # Assign the Category object
            product.category = category

            # Save the product
            product.save()

            # Variant details
            color = request.POST.get('color')
            size = request.POST.get('size')
            price = request.POST.get('price')
            stock = request.POST.get('stock')

            variant = ProductVariant.objects.create(
                product=product,
                color=color,
                size=size,
                price=price,
                stock=stock
            )

            # Product images
            images = request.FILES.getlist('images')

            for image in images:
                ProductImage.objects.create(
                    variant=variant,
                    image=image
                )

            return redirect('admin_products')

    else:
        product_form = ProductForm()

    return render(
        request,
        'admin_dashboard/add_product.html',
        {
            'product_form': product_form
        }
    )



@login_required
def view_product(request, id):

    if not request.user.is_superuser:
        return redirect('home')

    product = Product.objects.get(id=id)

    return render(
        request,
        'admin_dashboard/view_product.html',
        {
            'product': product,
        }
    )



@login_required
def edit_product(request, id):

    if not request.user.is_superuser:
        return redirect('home')

    product = Product.objects.get(id=id)

    if request.method == 'POST':

        form = ProductForm(
            request.POST,
            request.FILES,
            instance=product
        )

        if form.is_valid():
            form.save()

            return redirect('admin_products')

    else:

        form = ProductForm(
            instance=product
        )

    return render(
        request,
        'admin_dashboard/edit_product.html',
        {
            'form': form,
            'product': product,
        }
    )



@login_required
def delete_product(request, id):

    if not request.user.is_superuser:
        return redirect('home')

    product = Product.objects.get(id=id)

    if request.method == 'POST':

        product.delete()

        return redirect('admin_products')

    return render(
        request,
        'admin_dashboard/delete_product.html',
        {
            'product': product,
        }
    )



@login_required
def add_variant(request):

    if not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        form = ProductVariantForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('admin_products')

    else:
        form = ProductVariantForm()

    return render(
        request,
        'admin_dashboard/add_variant.html',
        {'form': form}
    )



@login_required
def product_variants(request, product_id):

    if not request.user.is_superuser:
        return redirect('home')

    from products.models import Product, ProductVariant

    product = Product.objects.get(id=product_id)

    variants = ProductVariant.objects.filter(
        product=product
    )

    return render(
        request,
        'admin_dashboard/variants.html',
        {
            'product': product,
            'variants': variants,
        }
    )



@login_required
def edit_variant(request, id):

    if not request.user.is_superuser:
        return redirect('home')

    from products.models import ProductVariant

    variant = ProductVariant.objects.get(id=id)

    if request.method == 'POST':
        form = ProductVariantForm(
            request.POST,
            instance=variant
        )

        if form.is_valid():
            form.save()

            return redirect(
                'product_variants',
                product_id=variant.product.id
            )

    else:
        form = ProductVariantForm(
            instance=variant
        )

    return render(
        request,
        'admin_dashboard/edit_variant.html',
        {
            'form': form,
            'variant': variant,
        }
    )



@login_required
def delete_variant(request, id):

    if not request.user.is_superuser:
        return redirect('home')

    from products.models import ProductVariant

    variant = ProductVariant.objects.get(id=id)

    if request.method == 'POST':
        product_id = variant.product.id
        variant.delete()

        return redirect(
            'product_variants',
            product_id=product_id
        )

    return render(
        request,
        'admin_dashboard/delete_variant.html',
        {
            'variant': variant,
        }
    )


@login_required
def add_address(request):

    if request.method == 'POST':

        form = AddressForm(request.POST)

        if form.is_valid():

            address = form.save(commit=False)
            address.user = request.user
            address.save()

            return redirect('checkout')

    else:

        form = AddressForm()

    return render(
        request,
        'accounts/add_address.html',
        {
            'form': form
        }
    )



def login_view(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            guest_items = request.session.pop('guest_cart_items', [])
            if guest_items:
                cart, _ = Cart.objects.get_or_create(user=user)

                for guest_item in guest_items:
                    variant = ProductVariant.objects.filter(
                        id=guest_item.get('variant_id'),
                        product_id=guest_item.get('product_id'),
                        stock__gt=0
                    ).first()
                    if not variant:
                        continue

                    cart_item, created = CartItem.objects.get_or_create(
                        cart=cart,
                        product_id=guest_item['product_id'],
                        variant=variant,
                        selected_size=guest_item.get('selected_size', ''),
                        defaults={'quantity': guest_item.get('quantity', 1)}
                    )
                    if not created:
                        cart_item.quantity += guest_item.get('quantity', 1)
                        cart_item.save(update_fields=['quantity'])

            guest_wishlist_ids = request.session.pop('guest_wishlist_items', [])
            if guest_wishlist_ids:
                wishlist, _ = Wishlist.objects.get_or_create(user=user)
                for product_id in guest_wishlist_ids:
                    WishlistItem.objects.get_or_create(
                        wishlist=wishlist,
                        product_id=product_id
                    )

            if user.is_superuser:
                return redirect('admin_dashboard')
            else:
                return redirect('home')

        else:

            return render(
                request,
                'accounts/login.html',
                {
                    'error': 'Invalid username or password'
                }
            )

    return render(
        request,
        'accounts/login.html'
    )




def register(request):

    if request.method == 'POST':

        form = RegisterForm(request.POST)

        if form.is_valid():

            form.save()

            return redirect('login')

    else:

        form = RegisterForm()

    return render(
        request,
        'accounts/register.html',
        {
            'form': form
        }
    )



@login_required
def profile(request):


    return render(
        request,
    'accounts/profile.html',
    {
        'user': request.user
    }
)



def logout_view(request):


    logout(request)

    return redirect('login')



@login_required
def dashboard(request):

    if not request.user.is_superuser:
        return redirect('home')

    return redirect('admin_dashboard')




@login_required
def admin_categories(request):

    if not request.user.is_superuser:
        return redirect('home')

    from products.models import Category

    category_queryset = Category.objects.select_related('parent').annotate(
        product_count=Count('product', distinct=True),
        collection_count=Count('subcategories', distinct=True)
    )
    top_level_count = Category.objects.filter(parent__isnull=True).count()
    collection_count = Category.objects.filter(parent__isnull=False).count()
    table_context = admin_table_context(
        request,
        category_queryset,
        ['name', 'description', 'parent__name'],
        [
            ('name', 'Category name', 'name'),
            ('parent', 'Parent category', 'parent__name'),
            ('collections', 'Collection count', 'collection_count'),
            ('products', 'Product count', 'product_count'),
        ],
        'parent'
    )

    return render(
        request,
        'admin_dashboard/categories.html',
        {
            'categories': table_context['page_obj'],
            'top_level_count': top_level_count,
            'collection_count': collection_count,
            **table_context,
        }
    )



@login_required
def add_category(request):

    if not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':

        form = CategoryForm(request.POST)

        if form.is_valid():

            form.save()

            return redirect('admin_categories')

    else:

        form = CategoryForm()

    return render(
        request,
        'admin_dashboard/add_category.html',
        {
            'form': form
        }
    )




@login_required
def edit_category(request, id):

    if not request.user.is_superuser:
        return redirect('home')

    from products.models import Category

    category = Category.objects.get(id=id)

    if request.method == 'POST':

        form = CategoryForm(
            request.POST,
            instance=category
        )

        if form.is_valid():

            form.save()

            return redirect('admin_categories')

    else:

        form = CategoryForm(instance=category)

    return render(
        request,
        'admin_dashboard/edit_category.html',
        {
            'form': form,
            'category': category
        }
    )



@login_required
def delete_category(request, id):

    if not request.user.is_superuser:
        return redirect('home')

    from products.models import Category

    category = Category.objects.get(id=id)

    if request.method == 'POST':

        category.delete()

        return redirect('admin_categories')

    return render(
        request,
        'admin_dashboard/delete_category.html',
        {
            'category': category
        }
    )


@login_required
def add_product_image(request, product_id):

    if not request.user.is_superuser:
        return redirect('home')

    from products.models import Product, ProductImage

    product = Product.objects.get(id=product_id)

    if request.method == 'POST':

        image = request.FILES.get('image')

        if image:
            ProductImage.objects.create(
                product=product,
                image=image
            )

            return redirect(
                'product_images',
                product_id=product.id
            )

    return render(
        request,
        'admin_dashboard/add_product_image.html',
        {
            'product': product,
        }
    )


@login_required
def product_images(request, product_id):

    if not request.user.is_superuser:
        return redirect('home')

    from products.models import Product, ProductImage

    product = Product.objects.get(id=product_id)

    images = ProductImage.objects.filter(
        product=product
    )

    return render(
        request,
        'admin_dashboard/product_images.html',
        {
            'product': product,
            'images': images,
        }
    )



@login_required
def delete_product_image(request, id):

    if not request.user.is_superuser:
        return redirect('home')

    from products.models import ProductImage

    image = ProductImage.objects.get(id=id)

    if request.method == 'POST':

        product_id = image.product.id

        image.delete()

        return redirect(
            'product_images',
            product_id=product_id
        )

    return render(
        request,
        'admin_dashboard/delete_product_image.html',
        {
            'image': image,
        }
    )



@login_required
def admin_orders(request):

    if not request.user.is_superuser:
        return redirect('home')

    from orders.models import Order, ReturnRequest

    order_queryset = Order.objects.select_related('return_request')
    pending_return_count = ReturnRequest.objects.filter(status='pending').count()
    table_context = admin_table_context(
        request,
        order_queryset,
        ['uuid', 'full_name', 'phone', 'status'],
        [
            ('created', 'Date placed', 'created_at'),
            ('customer', 'Customer', 'full_name'),
            ('total', 'Order total', 'total_amount'),
            ('status', 'Status', 'status'),
        ],
        'created'
    )

    return render(
        request,
        'admin_dashboard/orders.html',
        {
            'orders': table_context['page_obj'],
            'pending_return_count': pending_return_count,
            **table_context,
        }
    )



@login_required
def admin_order_detail(request, order_uuid):

    if not request.user.is_superuser:
        return redirect('home')

    from orders.models import Order

    order = get_object_or_404(Order, uuid=order_uuid)

    return render(
        request,
        'admin_dashboard/order_detail.html',
        {
            'order': order,
        }
    )



@login_required
@transaction.atomic
def update_order_status(request, order_uuid):

    if not request.user.is_superuser:
        return redirect('home')

    from orders.models import Order

    order = get_object_or_404(
        Order.objects.select_for_update(),
        uuid=order_uuid
    )

    if request.method == 'POST':

        status = request.POST.get('status')

        if status in dict(Order.STATUS_CHOICES):
            if order.status == 'Cancelled' and status != 'Cancelled':
                messages.error(
                    request,
                    'Cancelled orders cannot be reopened. Place a new order instead.'
                )
                return redirect('admin_order_detail', order_uuid=order.uuid)

            if status == 'Cancelled' and order.status != 'Cancelled':
                from orders.models import OrderItem

                reserved_items = OrderItem.objects.select_for_update().filter(
                    order=order,
                    stock_reserved=True,
                    stock_restored=False,
                    variant__isnull=False
                )
                for item in reserved_items:
                    ProductVariant.objects.filter(pk=item.variant_id).update(
                        stock=F('stock') + item.quantity
                    )
                    item.stock_restored = True
                    item.save(update_fields=['stock_restored'])

            order.status = status
            order.save()

        return redirect(
            'admin_order_detail',
            order_uuid=order.uuid
        )

    return redirect(
        'admin_order_detail',
        order_uuid=order.uuid
    )


@login_required
@transaction.atomic
def update_return_request(request, order_uuid):
    if not request.user.is_superuser:
        return redirect('home')

    from orders.models import Order, OrderItem, ReturnRequest

    order = get_object_or_404(Order, uuid=order_uuid)
    return_request = get_object_or_404(ReturnRequest, order=order)

    if request.method != 'POST':
        return redirect('admin_order_detail', order_uuid=order.uuid)

    status = request.POST.get('status', '')
    resolution = request.POST.get('resolution', '')
    valid_statuses = dict(ReturnRequest.STATUS_CHOICES)
    valid_resolutions = dict(ReturnRequest.RESOLUTION_CHOICES)

    if status not in valid_statuses:
        return redirect('admin_order_detail', order_uuid=order.uuid)
    if resolution and resolution not in valid_resolutions:
        return redirect('admin_order_detail', order_uuid=order.uuid)
    if status in ('approved', 'completed') and not resolution:
        return redirect('admin_order_detail', order_uuid=order.uuid)
    if status in ('pending', 'rejected'):
        resolution = ''

    restock_returned_items = request.POST.get('restock_returned_items') == 'on'
    if restock_returned_items and status != 'completed':
        messages.error(request, 'Mark the return request completed before restocking returned items.')
        return redirect('admin_order_detail', order_uuid=order.uuid)

    if restock_returned_items:
        returned_items = OrderItem.objects.select_for_update().filter(
            order=order,
            stock_reserved=True,
            stock_restored=False,
            variant__isnull=False
        )
        for item in returned_items:
            ProductVariant.objects.filter(pk=item.variant_id).update(
                stock=F('stock') + item.quantity
            )
            item.stock_restored = True
            item.save(update_fields=['stock_restored'])

    return_request.status = status
    return_request.resolution = resolution
    return_request.admin_note = request.POST.get('admin_note', '').strip()
    return_request.save()

    return redirect('admin_order_detail', order_uuid=order.uuid)



@login_required
def admin_users(request):

    if not request.user.is_superuser:
        return redirect('home')

    from .models import User

    user_queryset = User.objects.filter(
        is_superuser=False
    )
    table_context = admin_table_context(
        request,
        user_queryset,
        ['username', 'first_name', 'last_name', 'email', 'phone'],
        [
            ('username', 'Username', 'username'),
            ('name', 'Name', 'first_name'),
            ('email', 'Email', 'email'),
            ('joined', 'Date joined', 'date_joined'),
        ],
        'joined'
    )

    return render(
        request,
        'admin_dashboard/users.html',
        {
            'users': table_context['page_obj'],
            **table_context,
        }
    )



@login_required
def admin_addresses(request):

    if not request.user.is_superuser:
        return redirect('home')

    from .models import Address

    addresses = Address.objects.select_related(
        'user'
    ).order_by('-id')

    return render(
        request,
        'admin_dashboard/addresses.html',
        {
            'addresses': addresses,
        }
    )


@login_required
def admin_price_history(request):

    if not request.user.is_superuser:
        return redirect('home')

    from products.models import PriceHistory

    price_history_queryset = PriceHistory.objects.select_related(
        'variant',
        'variant__product'
    ).filter(
        price_type__in=['original', 'updated']
    ).exclude(
        variant__offers__isnull=False
    ).distinct().order_by(
        'variant__product__name',
        'variant_id',
        'start_date',
        'created_at'
    )
    table_context = admin_table_context(
        request,
        price_history_queryset,
        [
            'variant__product__name',
            'variant__color',
            'variant__size',
            'price_type',
        ],
        [
            ('sequence', 'Product and date', (
                'variant__product__name', 'variant_id', 'start_date', 'created_at'
            )),
            ('product', 'Product', 'variant__product__name'),
            ('date', 'Price effective date', 'start_date'),
            ('price', 'Price amount', 'price'),
            ('type', 'Price type', 'price_type'),
        ],
        'sequence'
    )

    return render(
        request,
        'admin_dashboard/price_history.html',
        {
            'price_history': table_context['page_obj'],
            **table_context,
        }
    )


@login_required
def admin_offers(request):

    if not request.user.is_superuser:
        return redirect('home')

    offer_queryset = Offer.objects.select_related(
        'variant',
        'variant__product'
    )
    table_context = admin_table_context(
        request,
        offer_queryset,
        [
            'variant__product__name',
            'variant__color',
            'variant__size',
        ],
        [
            ('product', 'Product', 'variant__product__name'),
            ('offer_price', 'Offer price', 'offer_price'),
            ('start', 'Start date', 'start_date'),
            ('end', 'End date', 'end_date'),
            ('created', 'Created', 'created_at'),
        ],
        'created'
    )
    offers = list(table_context['page_obj'].object_list)

    current_time = timezone.now()
    from products.models import PriceHistory

    offer_restored_prices = {
        (entry.variant_id, entry.start_date): entry.price
        for entry in PriceHistory.objects.filter(
            variant_id__in=[offer.variant_id for offer in offers],
            price_type='after_offer'
        )
    }
    base_price_history = {}
    for entry in PriceHistory.objects.filter(
        variant_id__in=[offer.variant_id for offer in offers],
        price_type__in=['original', 'updated', 'after_offer']
    ).order_by('variant_id', 'start_date', 'created_at'):
        base_price_history.setdefault(entry.variant_id, []).append(entry)

    for offer in offers:
        prices_before_offer = [
            entry for entry in base_price_history.get(offer.variant_id, [])
            if entry.start_date <= offer.start_date
            and (entry.end_date is None or entry.end_date >= offer.start_date)
        ]
        offer.price_before_offer = (
            prices_before_offer[-1].price
            if prices_before_offer else offer.variant.price
        )
        offer.restored_price = offer_restored_prices.get(
            (offer.variant_id, offer.end_date)
        )

        if not offer.is_active:
            offer.status = "Inactive"

        elif current_time < offer.start_date:
            offer.status = "Upcoming"

        elif current_time > offer.end_date:
            offer.status = "Expired"

        else:
            offer.status = "Active"

    return render(
        request,
        'admin_dashboard/offers.html',
        {
            'offers': offers,
            **table_context,
        }
    )


@login_required
@transaction.atomic
def add_price_history(request):

    if not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':

        form = PriceHistoryForm(request.POST)

        if form.is_valid():

            price_history = form.save(commit=False)

            variant = price_history.variant

            if price_history.price_type in ['original', 'updated']:
                ProductVariant.objects.filter(pk=variant.pk).update(
                    price=price_history.price
                )

            price_history.save()

            return redirect('admin_price_history')

    else:

        form = PriceHistoryForm()

    return render(
        request,
        'admin_dashboard/add_price_history.html',
        {
            'form': form,
        }
    )


@login_required
@transaction.atomic
def add_offer(request):

    if not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':

        form = OfferForm(request.POST)

        if form.is_valid():

            offer = form.save()

            return redirect('admin_offers')

    else:

        form = OfferForm()

    return render(
        request,
        'admin_dashboard/add_offer.html',
        {
            'form': form,
        }
    )



