from django.urls import path
from . import views
from .views import *

urlpatterns=[
    path('', views.sportix_home, name='sportix_home'),
    path('login/', views.sportix_login, name='sportix_login'),
    path('register',views.register),
    path('logout',views.sportix_logout),
    # -----admin----------
    path('add_category',views.add_category),
    path('add_product',views.add_product),
    path('admin_home/', views.admin_home, name='admin_home'),
    path('edit_product/<product_id>', views.edit_product),
    path('delete_pro/<id>',views.delete_pro),
    path('delete_category/<id>',views.delete_category),
    path('admin_orders',views.admin_orders),
    path("admin-orders/update/<int:order_id>/<str:status>/", views.update_order_status, name="update_order_status"),
    # --------user--------
    path('view_category/<int:id>/', views.view_category, name='view_category'),
    path('search/', views.search_products, name='search_products'),
    path('view_product/<id>',views.view_product),
    path("add_to_cart/<product_id>",views.add_to_cart),
    path("cart/",views.view_cart, name="view_cart"),
    path("remove_from_cart/<int:product_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("update_cart/<int:product_id>/<str:action>/",views.update_cart, name="update_cart"),
    path('contact',views.contact_us),
    path('checkout', views.checkout, name='checkout'),
    path('complete_order', views.verify_payment_and_complete_order, name='complete_order'),
    path('order_success',views.order_success),
    path('buy_now/<id>',views.buy_now),
    path('profile',views.user_profile),
    path('update_username',views.update_username),
    path("orders/cancel/<int:order_id>/", cancel_order, name="cancel_order"),
    path("create_razorpay_order/", create_razorpay_order, name="create_razorpay_order"),
    path("complete_razor_order/", complete_order, name="complete_order"),
    path("payment_success/", payment_success, name="payment_success"),
    path("payment_failed/", payment_failed, name="payment_failed"),
    path('complete_cod_order', views.complete_order),
     path('register/', register, name='register'),
    path('check-email/', check_email, name='check_email'),  # ✅ Fix added here
    path('verify-email/<uuid:token>/', verify_email, name='verify_email'),
]