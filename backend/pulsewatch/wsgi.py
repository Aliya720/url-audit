"""
WSGI config for PulseWatch project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pulsewatch.settings")
application = get_wsgi_application()
