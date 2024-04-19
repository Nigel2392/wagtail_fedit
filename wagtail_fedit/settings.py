from django.conf import settings



SIGN_SHARED_CONTEXT = getattr(settings, "WAGTAIL_FEDIT_SIGN_SHARED_CONTEXT", True)
"""
Sign the shared context with a secret key.
This is useful to prevent tampering with the shared context.
It will also be compressed with zlib if available.
It might not be in your site's security model to need this.
"""