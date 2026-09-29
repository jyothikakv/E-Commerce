from django.urls import path
from . import views

urlpatterns = [

    path('', views.product_list, name='product_list'),

    path('add/', views.add_product, name='add_product'),

    path('<int:id>/', views.product_detail, name='product_detail_legacy'),

    path('<slug:slug>/', views.product_detail, name='product_detail'),

    path('delete/<int:id>/', views.delete_product, name='delete_product'),

    path(
    'edit-images/<int:id>/',
    views.edit_product_images,
    name='edit_product_images'
    ),

    
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/<int:id>/', views.edit_category, name='edit_category'),
    path('categories/delete/<int:id>/', views.delete_category, name='delete_category'),

    
    path(
        'shop/categories/',
        views.customer_category_list,
        name='customer_category_list'
    ),
]