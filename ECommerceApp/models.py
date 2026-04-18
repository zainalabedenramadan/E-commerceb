import random
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, user_type='user', **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, user_type=user_type, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, user_type='admin', **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = (('admin', 'Admin'),('user', 'User'),)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    otp_code = models.CharField(max_length=6, blank=True, null=True)  # OTP مؤقت
    otp_created_at = models.DateTimeField(blank=True, null=True)      # وقت إنشاء OTP
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='user')  # نوع المستخدم
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
    
    def generate_otp(self):
        otp = str(random.randint(100000, 999999))
        self.otp_code = otp
        self.save(update_fields=['otp_code'])
        return otp

    def verify_otp(self, otp):
        if self.otp_code == otp:
            # مسح OTP بعد التحقق
            self.otp_code = None
            self.save(update_fields=['otp_code'])
            return True
        return False



class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} Profile"


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)  # اسم الشركة

    def __str__(self):
        return self.name


class ProductType(models.Model):
    name = models.CharField(max_length=255)  # اسم نوع المنتج
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='product_types')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'company'], name='unique_producttype_company')
        ]

    def __str__(self):
        return f"{self.name} - {self.company.name}"


class ProductDetail(models.Model):
    name = models.CharField(max_length=255)  # اسم المنتج
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # سعر المنتج
    description = models.TextField(blank=True, null=True)
    content = models.TextField()
    image = models.ImageField()
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE, related_name='products')

    def __str__(self):
        return self.name


class Cart(models.Model):
    cartcode = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(ProductDetail, related_name='prod', on_delete=models.CASCADE, default=2)
    quantity = models.IntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(quantity__gte=0), name="quantity_min_value")
        ]


class Order(models.Model):
    PAYMENT_STATUS_PENDING = 'p'
    PAYMENT_STATUS_COMPLETE = 'c'
    PAYMENT_STATUS_FAILED = 'f'

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PENDING, 'Pending'),
        (PAYMENT_STATUS_COMPLETE, 'Complete'),
        (PAYMENT_STATUS_FAILED, 'Failed'),
    ]

    placed_at = models.DateTimeField(auto_now_add=True)
    pending_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    complete_at = models.DateTimeField(null=True)

    def __str__(self):
        return self.pending_status

    @property
    def total_price(self):
        return sum(item.quantity * item.product.price for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(ProductDetail, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.product.name


class ChatRoom(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, unique=True)
    create = models.DateField(auto_now_add=True)


class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)





# from django.db import connection

# with connection.cursor() as cursor:
#     cursor.execute("DELETE FROM django_migrations;")