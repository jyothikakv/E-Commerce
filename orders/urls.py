from django.urls import path
from . import views


urlpatterns = [

    path('', views.order_list, name='order_list'),

    path(
        'place-order/',
        views.place_order,
        name='place_order'
    ),

    path(
        'success/<uuid:order_uuid>/',
        views.order_success,
        name='order_success'
    ),

    path(
        '<uuid:order_uuid>/return-request/',
        views.submit_return_request,
        name='submit_return_request'
    ),

    path(
        '<uuid:order_uuid>/',
        views.order_detail,
        name='order_detail'
    ),

]