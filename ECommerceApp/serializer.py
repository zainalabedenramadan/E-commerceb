# ==========================================================
# 📦 IMPORTS
# ==========================================================
import uuid
import os
import base64

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

from .models import (
    Company, ProductType, ProductDetail, Order, OrderItem,
    Cart, CartItem, Message, ChatRoom, Profile
)

User = get_user_model()

# ==========================================================
# 👤 AUTHENTICATION SERIALIZERS
# ==========================================================
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    user_type = serializers.ChoiceField(choices=User.USER_TYPE_CHOICES, default='user')

    class Meta:
        model = User
        fields = ['email', 'password', 'user_type']

    def create(self, validated_data):
        email = validated_data['email']
        validated_data['username'] = email.split('@')[0] + str(uuid.uuid4())[:5]
        user_type = validated_data.pop('user_type', 'user')
        return User.objects.create_user(user_type=user_type, **validated_data)

from .task import send_otp_email_task


def send_otp_email(user):
    otp = user.generate_otp()
    send_otp_email_task.delay(user.email, otp)  # هنا استدعاء Celery


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(
            request=self.context.get('request'),
            email=data.get('email'),
            password=data.get('password')
        )
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        send_otp_email(user)
        return user


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)

    def validate(self, attrs):
        if not attrs.get("refresh"):
            raise serializers.ValidationError({"refresh": "Refresh token is required."})
        return attrs


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'email', 'is_superuser', 'is_staff', 'password','user_type']

    def create(self, validated_data):
        email = validated_data['email']
        validated_data['username'] = email.split('@')[0] + str(uuid.uuid4())[:5]
        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


# ==========================================================
# 🏢 PRODUCT SERIALIZERS
# ==========================================================
class ProductDetailSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='product_type.company.name', read_only=True)
    producttype = serializers.CharField(source='product_type.name', read_only=True)

    class Meta:
        model = ProductDetail
        fields = [
            'id', 'name', 'price', 'image', 'content',
            'description', 'product_type', 'producttype', 'company_name'
        ]


class ProductDetailSerializerput(serializers.ModelSerializer):
    class Meta:
        model = ProductDetail
        fields = ['id', 'name', 'price', 'image', 'content', 'description', 'product_type']


class ProductTypeSerializer(serializers.ModelSerializer):
    products = ProductDetailSerializer(many=True, read_only=True)

    class Meta:
        model = ProductType
        fields = ['id', 'name', 'company', 'products']


class CompanySerializer(serializers.ModelSerializer):
    product_types = ProductTypeSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        fields = ['id', 'name', 'product_types']


class SimpleProductDetailSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='product_type.company.name', read_only=True)

    class Meta:
        model = ProductDetail
        fields = ['id', 'name', 'price', 'company_name', 'image']


# ==========================================================
# 🛒 CART SERIALIZERS
# ==========================================================
class CartItemserializer(serializers.ModelSerializer):
    product = SimpleProductDetailSerializer(read_only=True)
    Sub_total = serializers.SerializerMethodField(method_name='submain_total')

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'Sub_total']

    def submain_total(self, cartitem: CartItem):
        return cartitem.quantity * cartitem.product.price if cartitem.product else 0


class AddCartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()
    Sub_total = serializers.SerializerMethodField(method_name='submain_total')

    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'quantity', 'Sub_total']

    def save(self):
        cart_id = self.context['cart_id']
        product_id = self.validated_data['product_id']
        quantity = self.validated_data['quantity']

        try:
            cartitem = CartItem.objects.get(product_id=product_id, cart_id=cart_id)
            new_quantity = cartitem.quantity + quantity
            if new_quantity < 1:
                raise serializers.ValidationError({"quantity": "⚠️ لا يمكنك تقليل الكمية إلى أقل من 1."})
            cartitem.quantity = new_quantity
            cartitem.save()
            self.instance = cartitem
        except CartItem.DoesNotExist:
            self.instance = CartItem.objects.create(cart_id=cart_id, **self.validated_data)
        return self.instance

    def submain_total(self, cartitem: CartItem):
        return cartitem.quantity * cartitem.product.price


class Cartserializer(serializers.ModelSerializer):
    grand_total = serializers.SerializerMethodField(method_name='main_total')
    user = serializers.CharField(source='user.email', read_only=True)
    cart_id = serializers.UUIDField(read_only=True)
    items = CartItemserializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = '__all__'

    def main_total(self, cart: Cart):
        return sum(item.quantity * item.product.price for item in cart.items.all() if item.product)


# ==========================================================
# 💰 ORDER SERIALIZERS
# ==========================================================
class OrderItemSerializer(serializers.ModelSerializer):
    product = SimpleProductDetailSerializer()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    ownername = serializers.SerializerMethodField(method_name='get_owner')
    send_at = serializers.SerializerMethodField(method_name='get_placed_at')

    class Meta:
        model = Order
        fields = ['id', 'send_at', 'complete_at', 'pending_status', 'owner', 'ownername', 'items']

    def get_owner(self, obj: Order):
        return obj.owner.username.split('@')[0]

    def get_placed_at(self, obj: Order):
        return obj.placed_at.strftime("%Y-%#m-%#d %#H:%M")


class CreateOrderSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField()

    def save(self, **kwargs):
        with transaction.atomic():
            cart_id = self.validated_data['cart_id']
            user_id = self.context['user_id']
            order = Order.objects.create(owner_id=user_id)
            cartitems = CartItem.objects.filter(cart_id=cart_id)
            orderitems = [
                OrderItem(order=order, product=item.product, quantity=item.quantity)
                for item in cartitems
            ]
            OrderItem.objects.bulk_create(orderitems)
            cartitems.delete()
            return order


# ==========================================================
# 🔐 ENCRYPTION HELPERS
# ==========================================================
AES_KEY = b'12345678901234567890123456789012'  # 32-byte key for AES-256


def encrypt_message(plain_text: str) -> str:
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plain_text.encode()) + padder.finalize()
    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
    cipher_text = cipher.encryptor().update(padded_data) + cipher.encryptor().finalize()
    return base64.b64encode(iv + cipher_text).decode()


def decrypt_message(encrypted_message: str) -> str:
    try:
        if len(encrypted_message) % 4 != 0:
            encrypted_message += "=" * (4 - len(encrypted_message) % 4)
        encrypted_data = base64.b64decode(encrypted_message)
        iv, cipher_text = encrypted_data[:16], encrypted_data[16:]
        cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
        decrypted_data = cipher.decryptor().update(cipher_text) + cipher.decryptor().finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return (unpadder.update(decrypted_data) + unpadder.finalize()).decode('utf-8')
    except Exception as e:
        return f"[خطأ في فك التشفير: {e}]"


# ==========================================================
# 💬 MESSAGING SERIALIZERS
# ==========================================================
class MessageSerializer(serializers.ModelSerializer):
    roomname = serializers.CharField(source='room.name', read_only=True)
    content = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'roomname', 'sender', 'content', 'timestamp', 'is_read']

    def get_content(self, obj):
        return decrypt_message(obj.content)

    def create(self, validated_data):
        request = self.context.get('request')
        if request:
            validated_data['sender'] = request.user
        validated_data['content'] = encrypt_message(validated_data['content'])
        return super().create(validated_data)


class ChatRoomSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.email', read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['id', 'user_name', 'name', 'create', 'messages', 'unread_count']

    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()


# ==========================================================
# 🧍 PROFILE SERIALIZER
# ==========================================================
class ProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source='user.email')

    class Meta:
        model = Profile
        fields = ['id', 'user', 'user_email', 'full_name', 'bio', 'avatar']
        read_only_fields = ['user_email']


# class ImageUploadSerializer(serializers.Serializer):
#     image = serializers.ImageField()
    
#     class Meta:
#         fields = ['image']
# def get_image_url(self, obj):
#         request = self.context.get('request')
#         if obj.image:
#             return request.build_absolute_uri(obj.image.url)
#         return None
