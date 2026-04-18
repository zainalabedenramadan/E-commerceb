from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
     CurrentUserAPIView, LoginRequestOTPView, ProfileViewSet, RegisterViewSet, LogoutViewSet,UserViewSet,
    ChatRoomList, MessageList,VerifyOTPView,
    CompanyViewSet, ProductTypeViewSet, ProductDetailViewSet, ProductDetailViewSetput,
    CartViewSet, CartItemViewSet, OrderViewSet,MyProfileView
)

router = DefaultRouter()
router.register(r'api/companies', CompanyViewSet)
router.register(r'api/product-types', ProductTypeViewSet)
router.register(r'api/products', ProductDetailViewSet, basename='productdetail')
router.register(r'api/productsput', ProductDetailViewSetput, basename='productdetailput')
router.register(r'api/cart', CartViewSet, basename='cart')
router.register(r'api/orders', OrderViewSet, basename='orders')
router.register(r'api/room', ChatRoomList, basename='room')
router.register(r'api/message', MessageList, basename='message')
router.register(r'api/profiles', ProfileViewSet, basename='profile')
router.register(r'api/users', UserViewSet)
router.register(r'register', RegisterViewSet, basename='auth-register')
router.register(r'logout', LogoutViewSet, basename='auth-logout')
router.register(r'request-otp', LoginRequestOTPView, basename='auth-login')

cart_router = routers.NestedDefaultRouter(router, r'api/cart', lookup='zain')
cart_router.register('additems', CartItemViewSet, basename='cart-add-item')

urlpatterns = [
    path('api/message/<str:roomname>/', MessageList.as_view({'get': 'room_messages'})),
    path('mee/', CurrentUserAPIView.as_view(), name='current-user'),
    path('api/login/verify-otp/',VerifyOTPView.as_view(),name='otp'),
    path('api/profile/me/', MyProfileView.as_view()),
    path('', include(router.urls)),
    path('', include(cart_router.urls)),
    # path('upload-image/', ImageUploadView.as_view(), name='upload-image'),
]
