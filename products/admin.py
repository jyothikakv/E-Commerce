from django.contrib import admin
from django import forms

from .models import (
    Product,
    Category,
    ProductVariant,
    ProductImage,
    PriceHistory,
    Offer,
)


# =========================
# PRODUCT VARIANT INLINE
# =========================

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


# =========================
# PRODUCT IMAGE INLINE
# =========================

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


# =========================
# PRODUCT FORM
# =========================

class ProductAdminForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['category'].queryset = Category.objects.all()


# =========================
# PRODUCT ADMIN
# =========================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    form = ProductAdminForm

    list_display = (
        'name',
        'category',
        'fabric',
        'created_at',
    )

    inlines = [ProductVariantInline]


# =========================
# PRODUCT VARIANT ADMIN
# =========================

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):

    list_display = (
        'product',
        'size',
        'color',
        'stock',
        'price',
    )

    inlines = [ProductImageInline]


# =========================
# CATEGORY ADMIN
# =========================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'parent',
    )

    list_filter = (
        'parent',
    )

    search_fields = (
        'name',
    )


# =========================
# PRICE HISTORY ADMIN
# =========================

@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):

    list_display = (
        'variant',
        'price',
        'price_type',
        'start_date',
        'end_date',
        'created_at',
    )

    list_filter = (
        'price_type',
        'start_date',
        'end_date',
    )

    search_fields = (
        'variant__product__name',
        'variant__color',
        'variant__size',
    )

    ordering = ('-created_at',)


# =========================
# OFFER ADMIN
# =========================

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):

    list_display = (
        'variant',
        'offer_price',
        'start_date',
        'end_date',
        'is_active',
        'created_at',
    )

    list_filter = (
        'is_active',
        'start_date',
        'end_date',
    )

    search_fields = (
        'variant__product__name',
        'variant__color',
        'variant__size',
    )

    ordering = ('-created_at',)

