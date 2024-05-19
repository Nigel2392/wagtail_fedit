from wagtail import hooks
from django.urls import path, include
from ..hooks import (
    REGISTER_ADAPTER_CLASS,
    REGISTER_ADAPTER_URLS,
)
from ..urls import (
    urlpatterns as wagtail_fedit_urls,
)
from ..registry import (
    registry as adapter_registry,
)
from ..adapters import (
    FieldAdapter,
    DomPositionedFieldAdapter,
    BlockAdapter,
    DomPositionedBlockAdapter,
    ModelAdapter,
    BackgroundImageFieldAdapter,
)


adapter_registry.register(FieldAdapter)
adapter_registry.register(DomPositionedFieldAdapter)
adapter_registry.register(BlockAdapter)
adapter_registry.register(DomPositionedBlockAdapter)
adapter_registry.register(ModelAdapter)
adapter_registry.register(BackgroundImageFieldAdapter)


for hook in hooks.get_hooks(REGISTER_ADAPTER_CLASS):
    hook(adapter_registry)


@hooks.register("register_admin_urls")
def register_admin_urls():
    ns = "wagtail_fedit"

    urls = []
    for hook in hooks.get_hooks(REGISTER_ADAPTER_URLS):
        urls.extend(hook())

    urls.extend(wagtail_fedit_urls)

    return [
        path("fedit/", include((urls, ns), namespace=ns), name=ns),
    ]

