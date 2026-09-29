from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Q
from django.db import transaction
from products.models import (
    Product,
    ProductImage,
    ProductVariant,
    Offer,
    Category,
)

def product_detail(request, id=None, slug=None):

    if slug is not None:
        product = get_object_or_404(Product, slug=slug)
    else:
        product = get_object_or_404(Product, id=id)

    variants = product.variants.all()

    current_time = timezone.now()

    
    product.detail_images = []

    
    for variant in variants:

        for product_image in variant.images.all():

            if product_image.image:
                product.detail_images.append(product_image.image.url)

        
        active_offer = Offer.objects.filter(
            variant=variant,
            is_active=True,
            start_date__lte=current_time,
            end_date__gte=current_time
        ).first()

        variant.active_offer = active_offer

   
    if not product.detail_images and product.image:

        product.detail_images.append(product.image.url)

    return render(
        request,
        'products/product_detail.html',
        {
            'product': product,
            'variants': variants
        }
    )


from django.shortcuts import render, redirect, get_object_or_404
from .models import Category


def category_list(request):
    categories = Category.objects.all()
    return render(request, 'products/category_list.html', {
        'categories': categories
    })


def customer_category_list(request):

    categories = Category.objects.all()

    for category in categories:

        category.display_image_url = None

        products = category.product_set.all()

        for product in products:

            for variant in product.variants.all():

                first_image = variant.images.first()

                if first_image and first_image.image:
                    category.display_image_url = first_image.image.url
                    break

            if category.display_image_url:
                break

            if product.image:
                category.display_image_url = product.image.url
                break

    return render(
        request,
        'products/customer_category_list.html',
        {
            'categories': categories
        }
    )


def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')

        Category.objects.create(
            name=name,
            description=description
        )

        return redirect('category_list')

    return render(request, 'products/add_category.html')


def edit_category(request, id):
    category = get_object_or_404(Category, id=id)

    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.description = request.POST.get('description')
        category.save()

        return redirect('category_list')

    return render(request, 'products/edit_category.html', {
        'category': category
    })


def delete_category(request, id):
    category = get_object_or_404(Category, id=id)

    if request.method == 'POST':
        category.delete()
        return redirect('category_list')

    return render(request, 'products/delete_category.html', {
        'category': category
    })

@transaction.atomic
def add_product(request):

    if request.method == 'POST':

        name = request.POST.get('name')
        category_name = request.POST.get('category')
        description = request.POST.get('description')
        fabric = request.POST.get('fabric')

        category, created = Category.objects.get_or_create(
            name=category_name
        )

        product = Product.objects.create(
            name=name,
            category=category,
            description=description,
            fabric=fabric
        )

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

        images = request.FILES.getlist('images')

        for image in images:
            ProductImage.objects.create(
                variant=variant,
                image=image
            )

        return redirect('product_list')

    return render(request, 'products/add_product.html')


def edit_product_images(request, id):

    product = get_object_or_404(Product, id=id)

    variants = product.variants.all()

    if request.method == 'POST':

        image_id = request.POST.get('image_id')
        new_image = request.FILES.get('new_image')

        if image_id == 'product_image':

            if new_image:
                product.image = new_image
                product.save()

        else:

            product_image = get_object_or_404(
                ProductImage,
                id=image_id
            )

            if new_image:
                product_image.image = new_image
                product_image.save()

        return redirect(
            'edit_product_images',
            id=product.id
        )

    return render(
        request,
        'products/edit_product_images.html',
        {
            'product': product,
            'variants': variants
        }
    )


def delete_product(request, id):

    product = get_object_or_404(Product, id=id)

    if request.method == 'POST':
        product.delete()
        return redirect('product_list')

    return render(request, 'products/delete_product.html', {
        'product': product
    })

def product_list(request):
    search_query = request.GET.get('search', '').strip()
    category_name = request.GET.get('category', '').strip()
    category_display_name = ''
    selected_size = request.GET.get('size', '').strip()

    products = Product.objects.all()

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
        )

    if category_name:
        selected_category = Category.objects.filter(
            name__iexact=category_name
        ).first()

        if selected_category is None:
            normalized_category_name = slugify(category_name).replace('-', '')
            selected_category = next(
                (
                    category
                    for category in Category.objects.all()
                    if slugify(category.name).replace('-', '') == normalized_category_name
                ),
                None
            )

        if selected_category is None:
            raise Http404('Category not found')

        category_display_name = selected_category.name

        if selected_category.parent is None:
            products = products.filter(
                Q(category=selected_category) |
                Q(category__parent=selected_category)
            )
        else:
            products = products.filter(
                category=selected_category
            )

    products = list(products)

    size_labels = {
        's': 'S',
        'm': 'M',
        'l': 'L',
        'xl': 'XL',
        'xxl': 'XXL',
        'freesize': 'Free Size',
    }
    available_sizes = set()
    for product in products:
        for variant in product.variants.all():
            for size in variant.size.split(','):
                label = size.strip()
                normalized_size = label.lower().replace(' ', '')
                if normalized_size in size_labels:
                    available_sizes.add(size_labels[normalized_size])

    ordered_size_labels = ['S', 'M', 'L', 'XL', 'XXL', 'Free Size']
    available_sizes = [
        size for size in ordered_size_labels if size in available_sizes
    ]
    has_sized_products = any(size != 'Free Size' for size in available_sizes)

    if selected_size:
        normalized_size = selected_size.lower().replace(' ', '')
        products = [
            product
            for product in products
            if any(
                size.strip().lower().replace(' ', '') == normalized_size
                for variant in product.variants.all()
                for size in variant.size.split(',')
            )
        ]

    if request.user.is_authenticated:
        from wishlist.models import WishlistItem

        wishlisted_product_ids = set(
            WishlistItem.objects.filter(
                wishlist__user=request.user,
                product_id__in=[product.id for product in products]
            ).values_list('product_id', flat=True)
        )
    else:
        wishlisted_product_ids = set(
            request.session.get('guest_wishlist_items', [])
        )

    current_time = timezone.now()

    for product in products:
        product.is_wishlisted = product.id in wishlisted_product_ids
        product.display_image_url = None
        product.display_variant = None
        product.active_offer = None
        size_options = {}
        all_variants = list(product.variants.all())

        for variant in all_variants:

            variant_sizes = [
                size.strip()
                for size in variant.size.split(',')
                if size.strip()
            ]

            for size in variant_sizes:
                existing_option = size_options.get(size)
                if existing_option is None or (
                    existing_option.stock == 0 and variant.stock > 0
                ):
                    size_options[size] = variant

            if not product.display_variant:
                product.display_variant = variant

            image = variant.images.first()

            if image and image.image and not product.display_image_url:
                product.display_image_url = image.image.url
                product.display_variant = variant

        category = product.category
        category_names = [category.name.lower()]
        while category.parent_id:
            category = category.parent
            category_names.append(category.name.lower())

        product.is_saree = (
            'saree' in product.name.lower()
            or any('saree' in name for name in category_names)
        )

        if product.is_saree:
            free_size_variant = next(
                (variant for variant in all_variants if variant.stock > 0),
                all_variants[0] if all_variants else None
            )
            product.size_options = (
                [{
                    'id': free_size_variant.id,
                    'size': 'Free Size',
                    'stock': free_size_variant.stock,
                }]
                if free_size_variant else []
            )
        else:
            size_order = {'S': 0, 'M': 1, 'L': 2, 'XL': 3, 'XXL': 4}
            sorted_sizes = sorted(
                size_options.items(),
                key=lambda item: (
                    size_order.get(item[0].upper(), 5),
                    item[0].upper()
                )
            )
            product.size_options = [
                {
                    'id': variant.id,
                    'size': size,
                    'stock': variant.stock,
                }
                for size, variant in sorted_sizes
            ]

        product.selected_size_variant = None
        product.has_available_size = any(
            option['stock'] > 0 for option in product.size_options
        )
        if not product.display_image_url and product.image:
            product.display_image_url = product.image.url

        if product.display_variant:
            product.active_offer = Offer.objects.filter(
                variant=product.display_variant,
                is_active=True,
                start_date__lte=current_time,
                end_date__gte=current_time
            ).first()

    return render(
        request,
        'products/product_list.html',
        {
            'products': products,
            'search_query': search_query,
            'category_name': category_name,
            'category_display_name': category_display_name,
            'selected_size': selected_size,
            'available_sizes': available_sizes,
            'has_sized_products': has_sized_products,
        }
    )