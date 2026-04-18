from django.contrib import admin
from .models import User,Profile

from django.contrib import admin
from .models import Company, ProductType, ProductDetail,Cart,CartItem,Order,OrderItem,Message, ChatRoom 
from django.contrib.sessions.models import Session

admin.site.register(User)
admin.site.register(Profile)


admin.site.register(ChatRoom)
admin.site.register(Message)
admin.site.register(Company)
admin.site.register(ProductType)
admin.site.register(ProductDetail)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)


class SessionAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'expire_date', 'get_decoded_data']
    search_fields = ['session_key']

    def get_decoded_data(self, obj):
        # فك تشفير البيانات المخزنة في الجلسة
        return obj.get_decoded()

    get_decoded_data.short_description = 'Decoded Data'

admin.site.register(Session, SessionAdmin)





