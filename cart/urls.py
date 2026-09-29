from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),

    path('', views.cart_view, name='cart'),

    path(
        'add/<int:product_id>/',
        views.add_to_cart,
        name='add_to_cart'
    ),

    path(
        'increase/<int:item_id>/',
        views.increase_quantity,
        name='increase_quantity'
    ),

    path(
        'decrease/<int:item_id>/',
        views.decrease_quantity,
        name='decrease_quantity'
    ),

    path(
        'remove/<int:item_id>/',
        views.remove_from_cart,
        name='remove_from_cart'
    ),
]

