from rest_framework_simplejwt.tokens import RefreshToken
import os
from django.http import HttpResponse, Http404, FileResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import authenticate
from .models import Job, UserPayment, User  # Import your custom User model
from django.utils import timezone
from django.shortcuts import render, redirect
from django.conf import settings
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
stripe.api_key = settings.STRIPE_SECRET_KEY_TEST
import boto3
from botocore.exceptions import ClientError
from io import BytesIO  # For streaming S3 file content
s3_client = boto3.client('s3')
import logging
logger = logging.getLogger(__name__)
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.core.mail import send_mail
import csv
from io import StringIO
from .models import OneTimePayment  # Ensure OneTimePayment model is imported

# Password reset request view
class CustomPasswordResetView(PasswordResetView):
    email_template_name = 'registration/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')
    subject_template_name = 'registration/password_reset_subject.txt'
    template_name = 'registration/password_reset_form.html'

# Password reset confirm view (handle reset form submission)
class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    success_url = reverse_lazy('password_reset_complete')
    template_name = 'registration/password_reset_confirm.html'

def home(request):
    """
    A simple view to welcome users to the backend API.
    """
    return HttpResponse("Welcome to the InteLEAD backend. Use /signup, /login, /submit-job, etc.")


def payment_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            user_payment = UserPayment.objects.get(user=request.user)
            if not user_payment.payment_bool:
                return redirect('product_page')
        except UserPayment.DoesNotExist:
            return redirect('product_page')
        return view_func(request, *args, **kwargs)
    return wrapper

class SignupView(APIView):
    """
    Handles user registration using the custom MongoDB User model.
    """
    def post(self, request):
        data = request.data
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return Response({"message": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"message": "User already exists"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(email=email, password=password)

        return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    Handles user authentication and JWT token generation using the custom MongoDB User model.
    """
    def post(self, request):
        data = request.data
        email = data.get('email')
        password = data.get('password')

        user = authenticate(username=email, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({"token": str(refresh.access_token)}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)


class LoginView(APIView):
    """
    Handles user authentication and JWT token generation using the custom MongoDB User model.
    """
    def post(self, request):
        data = request.data
        email = data.get('email')
        password = data.get('password')

        user = authenticate(username=email, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({"token": str(refresh.access_token)}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)


class SubscriptionListView(APIView):
    """
    Retrieves the list of subscription plans available on Stripe.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            products = stripe.Product.list(active=True)
            subscriptions = []

            for product in products['data']:
                prices = stripe.Price.list(product=product['id'], active=True)
                for price in prices['data']:
                    subscriptions.append({
                        'id': price['id'],
                        'name': product['name'],
                        'price': price['unit_amount'] / 100,
                        'currency': price['currency'].upper(),
                        'interval': price['recurring']['interval'] if price['recurring'] else None
                    })

            return JsonResponse(subscriptions, safe=False)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class SubscribeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = request.data.get('token')
            subscription_id = request.data.get('subscriptionId')

            # Create a Stripe customer and subscription
            customer = stripe.Customer.create(
                email=request.user.email,
                source=token
            )

            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': subscription_id}],
                expand=['latest_invoice.payment_intent', 'plan']
            )

            # Save subscription details to UserPayment model
            user_payment = UserPayment.objects.get(user=request.user)
            user_payment.stripe_checkout_id = subscription.id
            user_payment.payment_bool = True

            # Set job limits based on the plan
            if subscription.plan.id == 'basic_plan':
                user_payment.max_jobs_allowed = 10
            elif subscription.plan.id == 'premium_plan':
                user_payment.max_jobs_allowed = 50
            else:
                user_payment.max_jobs_allowed = 100

            user_payment.save()

            return Response({"message": "Subscription successful"}, status=200)
        except stripe.error.StripeError as e:
            return Response({"message": str(e)}, status=400)
        
@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    def post(self, request):
        payload = request.body
        sig_header = request.META['HTTP_STRIPE_SIGNATURE']

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET_TEST
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return HttpResponse(status=400)

        # Handle subscription updates
        if event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            user_payment = UserPayment.objects.get(stripe_checkout_id=subscription.id)
            
            # Update subscription plan and job limit
            user_payment.subscription_plan = subscription.plan.id

            if subscription.plan.id == 'basic_plan':
                user_payment.max_jobs_allowed = 10
            elif subscription.plan.id == 'premium_plan':
                user_payment.max_jobs_allowed = 50
            else:
                user_payment.max_jobs_allowed = 100

            user_payment.save()

        return HttpResponse(status=200)


class UserDataView(APIView):
    """
    Retrieves the user's data.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({"username": user.username, "email": user.email}, status=status.HTTP_200_OK)


# Stripe Payment Views
class ProductPageView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return render(request, 'user_payment/product_page.html')

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY_TEST

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': settings.PRODUCT_PRICE,
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=settings.REDIRECT_DOMAIN + '/payment_successful?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=settings.REDIRECT_DOMAIN + '/payment_cancelled',
        )
        return redirect(checkout_session.url, code=303)


class PaymentSuccessfulView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY_TEST
        checkout_session_id = request.GET.get('session_id', None)
        session = stripe.checkout.Session.retrieve(checkout_session_id)
        customer = stripe.Customer.retrieve(session.customer)
        user_payment = UserPayment.objects.get(user=request.user)
        user_payment.stripe_checkout_id = checkout_session_id
        user_payment.payment_bool = True
        user_payment.save()
        return render(request, 'user_payment/payment_successful.html', {'customer': customer})


class PaymentCancelledView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return render(request, 'user_payment/payment_cancelled.html')
    

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """
    Handles Stripe webhook events for both subscription and one-time fee-based payments.
    """
    def post(self, request):
        payload = request.body
        sig_header = request.META['HTTP_STRIPE_SIGNATURE']

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET_TEST
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return HttpResponse(status=400)

        # Check event type
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            session_id = session.get('id', None)
            metadata = session.get('metadata', {})

            # Check if this is a subscription or one-time payment
            if 'subscription' in session['mode']:
                self.handle_subscription_payment(session_id)
            elif 'one_time' in metadata.get('payment_type', ''):
                self.handle_one_time_payment(session_id)

        elif event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            metadata = payment_intent.get('metadata', {})

            # Handle one-time fee payment
            if 'one_time' in metadata.get('payment_type', ''):
                self.handle_one_time_payment(payment_intent['id'])

        return HttpResponse(status=200)

    def handle_subscription_payment(self, session_id):
        """
        Handle Stripe subscription payments.
        """
        try:
            user_payment = UserPayment.objects.get(stripe_checkout_id=session_id)
            user_payment.payment_bool = True
            user_payment.save()
            logger.info(f"Subscription payment completed for session: {session_id}")
        except UserPayment.DoesNotExist:
            logger.error(f"Subscription payment record not found for session: {session_id}")

    def handle_one_time_payment(self, payment_id):
        """
        Handle Stripe one-time fee payments for post-processing.
        """
        try:
            one_time_payment = OneTimePayment.objects.get(stripe_payment_intent_id=payment_id)
            one_time_payment.payment_status = True
            one_time_payment.save()

            # Trigger the post-processing task after successful payment
            self.trigger_post_processing(one_time_payment.user, one_time_payment.job)
            logger.info(f"One-time payment completed for payment: {payment_id}")
        except OneTimePayment.DoesNotExist:
            logger.error(f"One-time payment record not found for payment: {payment_id}")

