from django.contrib import admin
from .models import Order, OrderItem, ReturnRequest


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        'uuid',
        'user',
        'full_name',
        'phone',
        'total_amount',
        'status',
        'created_at',
    )

    list_filter = (
        'status',
        'created_at',
    )

    search_fields = (
        'full_name',
        'phone',
        'user__username',
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):

    list_display = (
        'order',
        'product',
        'variant',
        'quantity',
        'price',
    )

    search_fields = (
        'product__name',
        'order__uuid',
    )


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):

    list_display = (
        'order',
        'requested_remedy',
        'status',
        'resolution',
        'created_at',
    )
    list_filter = ('status', 'requested_remedy', 'resolution')
    search_fields = ('order__uuid', 'order__full_name', 'reason')
