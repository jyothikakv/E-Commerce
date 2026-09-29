from django.urls import path

from .views import (
    login_view,
    register,
    profile,
    logout_view,
    dashboard,
    add_address,
    admin_dashboard,
    restock_variant,
    admin_products,
    admin_categories,
    add_category,
    edit_category,
    delete_category,
    add_product,
    add_variant,
    product_variants,
    edit_variant,
    delete_variant,
    edit_product,
    delete_product,
    view_product,
    add_product_image,
    product_images,
    delete_product_image,
    admin_orders,
    admin_order_detail,
    update_order_status,
    update_return_request,
    admin_users,
    admin_addresses,
    admin_price_history,
    add_price_history,
    admin_offers,
    add_offer,
)

urlpatterns = [

    path(
        'login/',
        login_view,
        name='login'
    ),


    path(
        'register/',
        register,
        name='register'
    ),


    path(
        'profile/',
        profile,
        name='profile'
    ),

    path(
    'address/add/',
    add_address,
    name='add_address'
    ),


    path(
        'logout/',
        logout_view,
        name='logout'
    ),


    path(
        'dashboard/',
        dashboard,
        name='dashboard'
    ),


    path(
        'admin-dashboard/',
        admin_dashboard,
        name='admin_dashboard'
    ),

    path(
        'admin-dashboard/stock/<int:variant_id>/restock/',
        restock_variant,
        name='restock_variant'
    ),


    path(
        'admin-dashboard/products/',
        admin_products,
        name='admin_products'
    ),


    path(
        'admin-dashboard/categories/',
        admin_categories,
        name='admin_categories'
    ),


    path(
        'admin-dashboard/categories/add/',
        add_category,
        name='add_category'
    ),


    path(
        'admin-dashboard/categories/edit/<int:id>/',
        edit_category,
        name='edit_category'
    ),


    path(
        'admin-dashboard/categories/delete/<int:id>/',
        delete_category,
        name='delete_category'
    ),


    path(
        'admin-dashboard/products/add/',
        add_product,
        name='add_product'
    ),


    path(
        'admin-dashboard/variants/add/',
        add_variant,
        name='add_variant'
    ),


    path(
        'admin-dashboard/products/<int:product_id>/variants/',
        product_variants,
        name='product_variants'
    ),


    path(
        'admin-dashboard/variants/edit/<int:id>/',
        edit_variant,
        name='edit_variant'
    ),


    path(
        'admin-dashboard/variants/delete/<int:id>/',
        delete_variant,
        name='delete_variant'
    ),


    path(
        'admin-dashboard/products/edit/<int:id>/',
        edit_product,
        name='edit_product'
    ),


    path(
        'admin-dashboard/products/delete/<int:id>/',
        delete_product,
        name='delete_product'
    ),


    path(
        'admin-dashboard/products/view/<int:id>/',
        view_product,
        name='view_product'
    ),


    path(
        'admin-dashboard/products/<int:product_id>/images/add/',
        add_product_image,
        name='add_product_image'
    ),


    path(
        'admin-dashboard/products/<int:product_id>/images/',
        product_images,
        name='product_images'
    ),


    path(
        'admin-dashboard/products/images/delete/<int:id>/',
        delete_product_image,
        name='delete_product_image'
    ),


    path(
        'admin-dashboard/orders/',
        admin_orders,
        name='admin_orders'
    ),


   path(
       'admin-dashboard/orders/<uuid:order_uuid>/',
       admin_order_detail,
       name='admin_order_detail'
   ),


   path(
       'admin-dashboard/orders/<uuid:order_uuid>/status/',
       update_order_status,
       name='update_order_status'
    ),

   path(
       'admin-dashboard/orders/<uuid:order_uuid>/return-request/',
       update_return_request,
       name='update_return_request'
    ),


   path(
       'admin-dashboard/users/',
       admin_users,
       name='admin_users'
    ),


   path(
       'admin-dashboard/addresses/',
       admin_addresses,
       name='admin_addresses'
   ),


   path(
       'admin-dashboard/price-history/',
       admin_price_history,
       name='admin_price_history'
    ),

   path(
       'admin-dashboard/offers/',
       admin_offers,
       name='admin_offers'
    ),

    path(
    'admin-dashboard/price-history/add/',
    add_price_history,
    name='add_price_history'
    ),

path('admin-dashboard/offers/', 
    admin_offers, 
    name='admin_offers'
    ),

path(
    'admin-dashboard/offers/add/',
    add_offer,
    name='add_offer'
    ),

]
