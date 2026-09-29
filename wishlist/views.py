from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import Wishlist, WishlistItem
from products.models import Product


@login_required
def wishlist_view(request):
    wishlist, created = Wishlist.objects.get_or_create(
        user=request.user
    )

    items = wishlist.items.select_related('product')

    return render(
        request,
        'wishlist/wishlist.html',
        {'wishlist': wishlist, 'items': items}
    )


def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wants_json = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.user.is_authenticated:
        wishlist, created = Wishlist.objects.get_or_create(
            user=request.user
        )

        item = WishlistItem.objects.filter(
            wishlist=wishlist,
            product=product
        ).first()
        if item and wants_json:
            item.delete()
            is_wishlisted = False
        else:
            WishlistItem.objects.get_or_create(
                wishlist=wishlist,
                product=product
            )
            is_wishlisted = True
        wishlist_count = wishlist.items.count()
    else:
        guest_items = request.session.get('guest_wishlist_items', [])
        is_wishlisted = product.id in guest_items
        if is_wishlisted and wants_json:
            guest_items.remove(product.id)
            request.session['guest_wishlist_items'] = guest_items
            is_wishlisted = False
        elif not is_wishlisted:
            guest_items.append(product.id)
            request.session['guest_wishlist_items'] = guest_items
            is_wishlisted = True
        wishlist_count = len(guest_items)

    if wants_json:
        return JsonResponse({
            'wishlist_count': wishlist_count,
            'is_wishlisted': is_wishlisted,
        })

    return redirect('wishlist')


@login_required
def remove_from_wishlist(request, product_id):
    wishlist = get_object_or_404(
        Wishlist,
        user=request.user
    )

    WishlistItem.objects.filter(
        wishlist=wishlist,
        product_id=product_id
    ).delete()

    return redirect('wishlist')
