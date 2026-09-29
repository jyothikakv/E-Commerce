import uuid
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

class Category(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    name = models.CharField(max_length=100)

    description = models.TextField(blank=True)

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories'
    )

    def __str__(self):

        if self.parent:
            return f"{self.parent.name} → {self.name}"

        return self.name

class Product(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    name = models.CharField(max_length=200)

    slug = models.SlugField(max_length=220, unique=True, blank=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE
    )

    description = models.TextField()


    fabric = models.CharField(
        max_length=100,
        blank=True
    )

    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'product'
            self.slug = base_slug
            suffix = 2

            while Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f'{base_slug}-{suffix}'
                suffix += 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductVariant(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'
    )

    size = models.CharField(max_length=20, blank=True)

    color = models.CharField(max_length=50, blank=True)

    stock = models.PositiveIntegerField(default=0)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        update_fields = kwargs.get('update_fields')
        track_price = update_fields is None or 'price' in update_fields
        previous_price = None

        if not is_new:
            previous_price = type(self).objects.filter(
                pk=self.pk
            ).values_list('price', flat=True).first()

        super().save(*args, **kwargs)

        if not track_price:
            return

        if is_new:
            PriceHistory.objects.create(
                variant=self,
                price=self.price,
                price_type='original',
                start_date=timezone.now()
            )
        elif previous_price is not None and previous_price != self.price:
            PriceHistory.objects.create(
                variant=self,
                price=self.price,
                price_type='updated',
                start_date=timezone.now()
            )

    def __str__(self):
        return f"{self.product.name} - {self.size} - {self.color}"


class PriceHistory(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='price_history'
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    price_type = models.CharField(
        max_length=30,
        choices=[
            ('original', 'Original Price'),
            ('offer', 'Offer Price'),
            ('updated', 'Updated Price'),
            ('after_offer', 'After Offer / Restored Price'),
        ]
    )

    start_date = models.DateTimeField()

    end_date = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        if self._state.adding and self.price_type in {'original', 'updated'}:
            self.variant.price_history.filter(
                price_type__in=['original', 'updated', 'after_offer'],
                end_date__isnull=True,
                start_date__lte=self.start_date
            ).update(end_date=self.start_date)

            self.variant.price_history.filter(
                price_type='after_offer',
                start_date__gt=self.start_date,
                end_date__isnull=True
            ).update(price=self.price)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.variant.product.name} - ₹{self.price}"


class Offer(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='offers'
    )

    offer_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    start_date = models.DateTimeField()

    end_date = models.DateTimeField()

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        price_changed = is_new

        if not is_new:
            previous_offer = type(self).objects.filter(
                pk=self.pk
            ).values('offer_price', 'start_date', 'end_date').first()
            price_changed = previous_offer is not None and any(
                previous_offer[field] != getattr(self, field)
                for field in ('offer_price', 'start_date', 'end_date')
            )

        super().save(*args, **kwargs)

        if price_changed and self.is_active:
            self.variant.price_history.filter(
                price_type__in=['original', 'updated', 'after_offer'],
                end_date__isnull=True,
                start_date__lte=self.start_date
            ).update(end_date=self.start_date)

            PriceHistory.objects.create(
                variant=self.variant,
                price=self.offer_price,
                price_type='offer',
                start_date=self.start_date,
                end_date=self.end_date
            )

            PriceHistory.objects.create(
                variant=self.variant,
                price=self.variant.price,
                price_type='after_offer',
                start_date=self.end_date
            )

    def __str__(self):
        return f"{self.variant.product.name} - ₹{self.offer_price}"


class ProductImage(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    variant = models.ForeignKey(
    ProductVariant,
    on_delete=models.CASCADE,
    related_name='images',
    null=True,
    blank=True
    )

    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.variant.product.name} - {self.variant.color}"