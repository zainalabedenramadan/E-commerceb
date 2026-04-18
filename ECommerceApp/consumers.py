
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from .models import ChatRoom, Message, Profile
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import os
import base64
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()

AES_KEY = b'12345678901234567890123456789012'  # مفتاح وهمي للتجربة

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group = f'chat_{self.room_name}'
        self.room = await sync_to_async(ChatRoom.objects.get)(name=self.room_name)

        await self.channel_layer.group_add(
            self.room_group,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(
            self.room_group,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']
        access_token = text_data_json.get('user')

        print("📩 Access Token المستلم:", access_token)

        try:
            token = AccessToken(access_token)
            user_id = token['user_id']
            user = await sync_to_async(User.objects.get)(id=user_id)
        except AuthenticationFailed:
            await self.send(text_data=json.dumps({
                "error": "تم التحقق من الـ token وفشل التوثيق"
            }))
            return
        except User.DoesNotExist:
            await self.send(text_data=json.dumps({
                "error": "المستخدم غير موجود"
            }))
            return

        await self.save_message(message_content, user)

        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "chat_message",
                "message": message_content,
                "user_id": user.id
            }
        )

    async def chat_message(self, event):
        message = event['message']
        user_id = event.get('user_id')
        user = await sync_to_async(User.objects.get)(id=user_id)

        try:
            profile = await sync_to_async(Profile.objects.get)(user=user)
            sender_name = profile.full_name.strip() if profile.full_name else user.email
        except Profile.DoesNotExist:
            sender_name = user.email

        unread_count = await sync_to_async(
            lambda: self.room.messages.filter(is_read=False).count()
        )()

        await self.send(text_data=json.dumps({
            "message": message,
            "sender": user_id,
            "sender_name": sender_name,
            "room_name": self.room_name,
            "unread_count": unread_count
        }))

    @sync_to_async
    def save_message(self, message_content, user):
        encrypted = self.encrypt_message(message_content)
        Message.objects.create(
            room=self.room,
            content=encrypted,
            sender=user
        )

    def encrypt_message(self, message):
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(message.encode()) + padder.finalize()

        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        return base64.b64encode(iv + encrypted_data).decode('utf-8')
