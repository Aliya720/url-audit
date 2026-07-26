# Celery application — PulseWatch
# TRD §10 — Scheduler Design

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pulsewatch.settings")

app = Celery("pulsewatch")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
