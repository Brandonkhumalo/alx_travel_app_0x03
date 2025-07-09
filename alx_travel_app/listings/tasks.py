# listings/tasks.py
from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_booking_confirmation_email(email, booking_info):
    subject = "Booking Confirmation"
    message = f"Your booking was successful!\n\nDetails:\n{booking_info}"
    send_mail(subject, message, 'your-email@gmail.com', [email])
