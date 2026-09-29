import uuid
from django.db import models
from django.conf import settings
from products.models import Product, ProductVariant


class Order(models.Model):

    uuid = models.UUIDField(
    default=uuid.uuid4,
    editable=False,
    unique=True
)

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    full_name = models.CharField(max_length=150)

    phone = models.CharField(max_length=15)

    address = models.TextField()

    city = models.CharField(max_length=100)

    state = models.CharField(max_length=100)

    pincode = models.CharField(max_length=10)

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Order {self.uuid}"


class ReturnRequest(models.Model):

    REQUESTED_REMEDY_CHOICES = [
        ('exchange', 'Exchange product'),
        ('refund', 'Refund money'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]

    RESOLUTION_CHOICES = [
        ('exchange', 'Exchange product'),
        ('refund', 'Refund money'),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='return_request'
    )
    requested_remedy = models.CharField(
        max_length=20,
        choices=REQUESTED_REMEDY_CHOICES
    )
    reason = models.TextField(max_length=1000)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    resolution = models.CharField(
        max_length=20,
        choices=RESOLUTION_CHOICES,
        blank=True
    )
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Return request for order {self.order.uuid}"


class OrderItem(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    selected_size = models.CharField(max_length=20, blank=True)

    quantity = models.PositiveIntegerField(
        default=1
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    stock_reserved = models.BooleanField(default=False)
    stock_restored = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"


