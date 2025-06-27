from rest_framework import viewsets
from .models import Listing, Booking
from .serializers import ListingSerializer, BookingSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Payment
from django.conf import settings

class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(host=self.request.user)


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(guest=self.request.user)

CHAPA_SECRET_KEY = settings.CHAPA_SECRET_KEY
CHAPA_BASE_URL = "https://api.chapa.co/v1/transaction"

class InitiatePaymentView(APIView):
    def post(self, request):
        booking_reference = request.data.get("booking_reference")
        amount = request.data.get("amount")
        customer_email = request.data.get("email")
        currency = request.data.get("currency", "ETB")  # default to Ethiopian Birr

        # Prepare payload for Chapa payment initiation
        payload = {
            "amount": amount,
            "currency": currency,
            "email": customer_email,
            "tx_ref": booking_reference,
            "callback_url": "https://your-domain.com/api/payment/verify/",
            "return_url": "https://your-domain.com/payment-success/",
        }

        headers = {
            "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        # Initiate payment
        response = requests.post(f"{CHAPA_BASE_URL}/initialize", json=payload, headers=headers)
        data = response.json()

        if response.status_code == 200 and data.get("status") == "success":
            payment_link = data["data"]["checkout_url"]
            transaction_id = data["data"]["id"]

            # Save payment with status Pending
            Payment.objects.update_or_create(
                booking_reference=booking_reference,
                defaults={
                    "transaction_id": transaction_id,
                    "amount": amount,
                    "status": "Pending",
                }
            )
            return Response({"payment_link": payment_link}, status=status.HTTP_200_OK)
        else:
            return Response({"error": data.get("message", "Failed to initiate payment.")}, status=status.HTTP_400_BAD_REQUEST)
        
class VerifyPaymentView(APIView):
    def get(self, request):
        tx_ref = request.GET.get("tx_ref")

        if not tx_ref:
            return Response({"error": "Transaction reference (tx_ref) missing."}, status=status.HTTP_400_BAD_REQUEST)

        headers = {
            "Authorization": f"Bearer {CHAPA_SECRET_KEY}"
        }

        response = requests.get(f"{CHAPA_BASE_URL}/verify/{tx_ref}", headers=headers)
        data = response.json()

        if response.status_code == 200 and data.get("status") == "success":
            payment_data = data.get("data", {})
            status_from_chapa = payment_data.get("status")
            booking_reference = payment_data.get("tx_ref")

            payment = Payment.objects.filter(booking_reference=booking_reference).first()
            if not payment:
                return Response({"error": "Payment record not found."}, status=status.HTTP_404_NOT_FOUND)

            if status_from_chapa == "success":
                payment.status = "Completed"
                # Here you can trigger email sending via Celery task
            elif status_from_chapa == "failed":
                payment.status = "Failed"
            payment.save()

            return Response({"status": payment.status}, status=status.HTTP_200_OK)
        else:
            return Response({"error": data.get("message", "Verification failed.")}, status=status.HTTP_400_BAD_REQUEST)