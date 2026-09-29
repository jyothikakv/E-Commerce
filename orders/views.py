from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from types import SimpleNamespace

from cart.models import Cart
from products.models import ProductVariant, Offer
from accounts.models import Address

from .models import Order, OrderItem, ReturnRequest


@login_required
def order_list(request):

    orders = Order.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(
        request,
        'orders/order_list.html',
        {
            'orders': orders
        }
    )


@login_required
@transaction.atomic
def place_order(request):

    if request.method != 'POST':
        return redirect('cart')

    buy_now_variant_id = request.session.get('buy_now_variant_id')

    if buy_now_variant_id:
        variant = get_object_or_404(
            ProductVariant.objects.select_related('product'),
            id=buy_now_variant_id,
            stock__gt=0
        )
        order_items = [SimpleNamespace(
            product=variant.product,
            variant=variant,
            selected_size=request.session.get('buy_now_selected_size', ''),
            quantity=1
        )]
        cart_items_to_clear = []
    else:
        cart = get_object_or_404(Cart, user=request.user)
        cart_items_to_clear = list(cart.items.select_related('product', 'variant'))
        order_items = cart_items_to_clear

    if not order_items:
        return redirect('cart')

    address_id = request.POST.get('selected_address')

    if not address_id:
        return redirect('checkout')

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    requested_stock = {}
    for item in order_items:
        if item.variant:
            variant_id = item.variant.pk
            requested_stock[variant_id] = (
                requested_stock.get(variant_id, 0) + item.quantity
            )

    locked_variants = ProductVariant.objects.select_for_update().in_bulk(
        requested_stock
    )
    if any(
        variant_id not in locked_variants
        or locked_variants[variant_id].stock < quantity
        for variant_id, quantity in requested_stock.items()
    ):
        messages.error(
            request,
            'One or more items no longer have enough stock. Review your order and try again.'
        )
        return redirect('checkout')

    for variant_id, quantity in requested_stock.items():
        ProductVariant.objects.filter(pk=variant_id).update(
            stock=F('stock') - quantity
        )

    total_amount = 0

    current_time = timezone.now()

    for item in order_items:

        if item.variant:

            active_offer = Offer.objects.filter(
                variant=item.variant,
                is_active=True,
                start_date__lte=current_time,
                end_date__gte=current_time
            ).first()

            if active_offer:
                price = active_offer.offer_price
            else:
                price = item.variant.price

        else:
            price = 0

        total_amount += price * item.quantity

    order = Order.objects.create(
        user=request.user,
        full_name=address.full_name,
        phone=address.phone,
        address=address.address,
        city=address.city,
        state=address.state,
        pincode=address.pincode,
        total_amount=total_amount,
        status='Pending'
    )

    for item in order_items:

        if item.variant:

            active_offer = Offer.objects.filter(
                variant=item.variant,
                is_active=True,
                start_date__lte=current_time,
                end_date__gte=current_time
            ).first()

            if active_offer:
                price = active_offer.offer_price
            else:
                price = item.variant.price

        else:
            price = 0

        OrderItem.objects.create(
            order=order,
            product=item.product,
            variant=item.variant,
            selected_size=item.selected_size,
            quantity=item.quantity,
            price=price,
            stock_reserved=bool(item.variant)
        )

    if cart_items_to_clear:
        for item in cart_items_to_clear:
            item.delete()

    request.session.pop('buy_now_variant_id', None)
    request.session.pop('buy_now_selected_size', None)

    return redirect(
        'order_success',
        order_uuid=order.uuid
    )


@login_required
def order_success(request, order_uuid):

    order = get_object_or_404(
        Order,
        uuid=order_uuid,
        user=request.user
    )

    return render(
        request,
        'orders/order_success.html',
        {
            'order': order
        }
    )


@login_required
def order_detail(request, order_uuid):
    order = get_object_or_404(
        Order.objects.prefetch_related(
            'items__product',
            'items__variant__images'
        ),
        uuid=order_uuid,
        user=request.user
    )

    tracking_steps = [
        ('Pending', 'Order placed'),
        ('Confirmed', 'Confirmed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
    ]
    status_positions = {status: position for position, (status, _) in enumerate(tracking_steps)}

    return render(
        request,
        'orders/order_detail.html',
        {
            'order': order,
            'return_request': getattr(order, 'return_request', None),
            'tracking_steps': tracking_steps,
            'current_status_position': status_positions.get(order.status, -1),
        }
    )


@login_required
def submit_return_request(request, order_uuid):
    if request.method != 'POST':
        return redirect('order_detail', order_uuid=order_uuid)

    order = get_object_or_404(
        Order,
        uuid=order_uuid,
        user=request.user
    )

    if order.status != 'Delivered' or hasattr(order, 'return_request'):
        return redirect('order_detail', order_uuid=order_uuid)

    requested_remedy = request.POST.get('requested_remedy', '')
    reason = request.POST.get('reason', '').strip()
    valid_remedies = dict(ReturnRequest.REQUESTED_REMEDY_CHOICES)
    error = None

    if requested_remedy not in valid_remedies:
        error = 'Choose whether you would like an exchange or refund.'
    elif not reason:
        error = 'Enter a reason for your request.'
    elif len(reason) > 1000:
        error = 'Your reason must be 1000 characters or fewer.'

    if error:
        tracking_steps = [
            ('Pending', 'Order placed'),
            ('Confirmed', 'Confirmed'),
            ('Shipped', 'Shipped'),
            ('Delivered', 'Delivered'),
        ]
        return render(
            request,
            'orders/order_detail.html',
            {
                'order': order,
                'tracking_steps': tracking_steps,
                'current_status_position': 3,
                'return_error': error,
            },
            status=400
        )

    ReturnRequest.objects.create(
        order=order,
        requested_remedy=requested_remedy,
        reason=reason
    )
    return redirect('order_detail', order_uuid=order_uuid)