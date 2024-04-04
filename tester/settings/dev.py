from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-dg_)1@s1$(3o!kj9#_jsjg%it(w2*+y82$!0#4#&2^w324w#l$"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


try:
    from .local import *
except ImportError:
    pass
