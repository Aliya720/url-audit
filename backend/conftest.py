import os

# Clear DATABASE_URL during test suite execution to use SQLite fallback
os.environ["DATABASE_URL"] = ""
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pulsewatch.settings")

import django  # noqa: E402

django.setup()
