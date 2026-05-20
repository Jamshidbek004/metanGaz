import os
import sys

path = '/home/onlymetan/metanGaz'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'startapp.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
