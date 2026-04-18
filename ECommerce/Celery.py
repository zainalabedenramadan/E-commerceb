import os
from celery import Celery

# إعداد متغير البيئة لمشروع Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ECommerce.settings')

# إنشاء تطبيق Celery
app = Celery('')

# تحميل إعدادات Celery من settings.py مع استخدام namespace 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# اكتشاف المهام تلقائيًا في جميع التطبيقات المثبتة داخل INSTALLED_APPS
app.autodiscover_tasks()

# تسجيل مهمة اختبارية للتأكد أن Celery يعمل
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
