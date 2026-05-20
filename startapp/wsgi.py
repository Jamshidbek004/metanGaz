import os
import sys

# Loyiha yo'lagini qo'shamiz
path = '/home/onlymetan/metanGaz'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'startapp.settings'

from django.core.wsgi import get_wsgi_application
django_app = get_wsgi_application()

# WhiteNoise orqali static fayllarni to'g'ridan-to'g'ri serve qilish
try:
    from whitenoise import WhiteNoise
    application = WhiteNoise(django_app, root='/home/onlymetan/metanGaz/static', prefix='static')
except ImportError:
    application = django_app
