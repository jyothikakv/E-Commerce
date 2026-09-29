from cart.models import CartItem
from wishlist.models import WishlistItem


def shopping_counts(request):
    cart_count = 0
    wishlist_count = 0

    if request.user.is_authenticated:
        cart_count = sum(
            CartItem.objects.filter(cart__user=request.user).values_list(
                'quantity', flat=True
            )
        )
        wishlist_count = WishlistItem.objects.filter(
            wishlist__user=request.user
        ).count()
    else:
        cart_count = sum(
            item.get('quantity', 0)
            for item in request.session.get('guest_cart_items', [])
        )
        wishlist_count = len(request.session.get('guest_wishlist_items', []))

    return {
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
    }