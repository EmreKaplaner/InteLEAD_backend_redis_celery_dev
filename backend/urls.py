from django.contrib import admin
from django.urls import path, include
from . import views

# Custom Password Reset Views
from .views import CustomPasswordResetView, CustomPasswordResetConfirmView

api_patterns = [
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('product_page/', views.ProductPageView.as_view(), name='product_page'),
    path('payment_successful/', views.PaymentSuccessfulView.as_view(), name='payment_successful'),
    path('payment_cancelled/', views.PaymentCancelledView.as_view(), name='payment_cancelled'),
    path('stripe_webhook/', views.StripeWebhookView.as_view(), name='stripe_webhook'),
    path('subscriptions/', views.SubscriptionListView.as_view(), name='subscriptions'),
    path('subscribe/', views.SubscribeView.as_view(), name='subscribe'),

    # Custom password reset views
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', CustomPasswordResetView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', CustomPasswordResetConfirmView.as_view(), name='password_reset_complete'),
]

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include(api_patterns)),  # Group all API routes under /api/
]
