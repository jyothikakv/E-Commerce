from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from types import SimpleNamespace

from .models import Cart, CartItem
from products.models import Product, ProductVariant, Offer


def add_to_cart(request, product_id):

    wants_json = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    product = get_object_or_404(
        Product,
        id=product_id
    )

    variant_id = request.POST.get('variant') or request.GET.get('variant')

    if not variant_id:
        if wants_json:
            return JsonResponse({'error': 'Select a size first.'}, status=400)
        return redirect('product_detail', slug=product.slug)

    variant = get_object_or_404(
        ProductVariant,
        id=variant_id,
        product=product,
        stock__gt=0
    )

    available_sizes = [
        size.strip()
        for size in variant.size.split(',')
        if size.strip()
    ]
    selected_size = request.POST.get('selected_size', '').strip()

    if not selected_size:
        if any(size.lower().replace(' ', '') == 'freesize' for size in available_sizes):
            selected_size = 'Free Size'
        elif available_sizes:
            selected_size = available_sizes[0]

    normalized_size = selected_size.lower().replace(' ', '')
    if not any(
        size.lower().replace(' ', '') == normalized_size
        for size in available_sizes
    ):
        if wants_json:
            return JsonResponse({'error': 'Select a valid size.'}, status=400)
        return redirect('product_detail', slug=product.slug)

    if request.POST.get('purchase_action') == 'buy_now':
        request.session['buy_now_variant_id'] = variant.id
        request.session['buy_now_selected_size'] = selected_size
        return redirect('checkout')

    request.session.pop('buy_now_variant_id', None)
    request.session.pop('buy_now_selected_size', None)

    if not request.user.is_authenticated:
        guest_items = request.session.get('guest_cart_items', [])
        matching_item = next(
            (
                item for item in guest_items
                if item['variant_id'] == variant.id
                and item['selected_size'] == selected_size
            ),
            None
        )

        if matching_item:
            matching_item['quantity'] += 1
        else:
            guest_items.append({
                'product_id': product.id,
                'variant_id': variant.id,
                'selected_size': selected_size,
                'quantity': 1,
            })

        request.session['guest_cart_items'] = guest_items
        cart_count = sum(item['quantity'] for item in guest_items)
        if wants_json:
            return JsonResponse({'cart_count': cart_count})
        return redirect('product_list')

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        selected_size=selected_size
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    if wants_json:
        cart_count = sum(
            cart.items.values_list('quantity', flat=True)
        )
        return JsonResponse({'cart_count': cart_count})

    return redirect('cart')


@login_required
def increase_quantity(request, item_id):

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    cart_item.quantity += 1
    cart_item.save()

    return redirect('cart')


@login_required
def decrease_quantity(request, item_id):

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()

    return redirect('cart')



@login_required
def remove_from_cart(request, item_id):

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    cart_item.delete()

    return redirect('cart')



@login_required
def cart_view(request):

    request.session.pop('buy_now_variant_id', None)
    request.session.pop('buy_now_selected_size', None)

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    current_time = timezone.now()

    cart_items = list(cart.items.select_related('product', 'variant'))
    total = 0

    for item in cart_items:

        if item.variant:

            active_offer = Offer.objects.filter(
                variant=item.variant,
                is_active=True,
                start_date__lte=current_time,
                end_date__gte=current_time
            ).first()

            item.unit_price = active_offer.offer_price if active_offer else item.variant.price
            item.item_total = item.unit_price * item.quantity
        else:
            item.unit_price = 0
            item.item_total = 0

        total += item.item_total

    return render(
        request,
        'cart/cart.html',
        {
            'cart': cart,
            'cart_items': cart_items,
            'total': total,
        }
    )


@login_required
def checkout(request):

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    current_time = timezone.now()

    buy_now_variant_id = request.session.get('buy_now_variant_id')
    if buy_now_variant_id:
        variant = get_object_or_404(
            ProductVariant.objects.select_related('product'),
            id=buy_now_variant_id,
            stock__gt=0
        )
        active_offer = Offer.objects.filter(
            variant=variant,
            is_active=True,
            start_date__lte=current_time,
            end_date__gte=current_time
        ).first()
        unit_price = active_offer.offer_price if active_offer else variant.price
        cart_items = [SimpleNamespace(
            product=variant.product,
            variant=variant,
            selected_size=request.session.get('buy_now_selected_size', ''),
            quantity=1,
            unit_price=unit_price,
            item_total=unit_price
        )]
        total = unit_price
    else:
        cart_items = list(cart.items.select_related('product', 'variant'))
        total = 0

    if not buy_now_variant_id:
        for item in cart_items:

            if item.variant:
                active_offer = Offer.objects.filter(
                    variant=item.variant,
                    is_active=True,
                    start_date__lte=current_time,
                    end_date__gte=current_time
                ).first()

                if active_offer:
                    item.unit_price = active_offer.offer_price
                else:
                    item.unit_price = item.variant.price

                item.item_total = item.unit_price * item.quantity
                total += item.item_total
            else:
                item.unit_price = 0
                item.item_total = 0

    addresses = request.user.addresses.all()

    return render(
    request,
    'cart/checkout.html',
    {
        'cart': cart,
        'cart_items': cart_items,
        'total': total,
        'addresses': addresses,
    }
)