from django.conf import settings



SIGN_SHARED_CONTEXT = getattr(settings, "WAGTAIL_FEDIT_SIGN_SHARED_CONTEXT", True)
"""
Sign the shared context with a secret key.
This is useful to prevent tampering with the shared context.
It will also be compressed with zlib if available.
It might not be in your site's security model to need this.
"""


SHARE_WITH_SESSIONS = getattr(settings, "WAGTAIL_FEDIT_SHARE_WITH_SESSIONS", False)
"""
Share the context with the session.
This is useful if you are running into limits with the URL length.
This will store the context in the session and pass the session
key to the iFrame instead of the context.
"""

USE_ADAPTER_SESSION_ID = getattr(settings, "WAGTAIL_FEDIT_USE_ADAPTER_SESSION_ID", True)
"""
Use the get_element_id method of the adapter to generate a session ID.
This is useful to not clutter session data too much.
If `False`, the session ID will be generated each time the page is loaded.
"""

TRACK_LOCALES = getattr(settings, "WAGTAIL_FEDIT_TRACK_LOCALES", False)
"""
Track the locales of the users across the views.
**This sets the initial request.LANGUAGE_CODE (if available) in the shared context.**
If this is false, there is no guarantee that the language of a saved field/model
will be the same as it initially was, generally it will be - however this might mess up with Wagtail's `Page.locale` and
the page not being available in the context afterwards. If that is the case, set this to `True`.
"""

TIPPY_ENABLED = getattr(settings, "WAGTAIL_FEDIT_TIPPY_ENABLED", True)
"""
Enable Tippy.js tooltips for toolbar buttons.
"""

