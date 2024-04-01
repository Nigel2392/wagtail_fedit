from wagtail import hooks
from django.urls import path, include
from ..urls import urlpatterns as wagtail_fedit_urls

@hooks.register("register_admin_urls")
def register_admin_urls():
    ns = "wagtail_fedit"
    urls = (wagtail_fedit_urls, ns)
    return [
        path("fedit/", include(urls, namespace=ns), name=ns)
    ]


