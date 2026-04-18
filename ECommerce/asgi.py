import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ECommerce.settings')
from django.core.asgi import get_asgi_application
application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path  # تغيير من path إلى re_path
from ECommerceApp.consumers import ChatConsumer


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            re_path(r'^ws/chat/(?P<room_name>\w+)/$', ChatConsumer.as_asgi()),
        ])
    ),
})
