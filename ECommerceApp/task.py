from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings  # لاستدعاء DEFAULT_FROM_EMAIL

@shared_task
def send_otp_email_task(email, otp):
    send_mail('Your OTP Code',f'Your OTP code is {otp}',
        settings.DEFAULT_FROM_EMAIL,  # الآن يظهر البريد الفعلي من الإعدادات
        [email],
        fail_silently=False,
    )
