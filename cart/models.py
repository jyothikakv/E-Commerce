import uuid
from django.db import models
from django.conf import settings
from products.models import Product, ProductVariant


class Cart(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Cart"


class CartItem(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    selected_size = models.CharField(max_length=20, blank=True)

    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):

        if self.variant:
            return (
                f"{self.product.name} - "
                f"{self.variant.color} - "
                f"{self.selected_size or self.variant.size} - "
                f"{self.quantity}"
            )

        return f"{self.product.name} - {self.quantity}"