import uuid
from django.db import models
from django.conf import settings
from products.models import Product


class Wishlist(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username}'s Wishlist"


class WishlistItem(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    added_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['wishlist', 'product'],
                name='unique_wishlist_product'
            )
        ]

    def __str__(self):
        return self.product.name


