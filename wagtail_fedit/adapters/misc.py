from django.http import HttpRequest
from django.utils.functional import classproperty
from .base import Keyword
from .field import (
    FieldAdapter,
)
from .funcs import (
    BaseFieldFuncAdapter,
)

from wagtail.images.models import Filter
from wagtail.images.utils import to_svg_safe_spec
from wagtail.images.shortcuts import (
    get_rendition_or_not_found,
)


class BackgroundImageFieldAdapter(BaseFieldFuncAdapter):
    """
    Adapter for background-images.
    On succesful form submission; will return the URL of the image.
    This is placed in the background-image property of the target element. 
    """
    inline = True
    identifier = "field_bg_image"
    usage_description = "This adapter is used for changing a css property of a target element to a background-image."
    keywords = (
        Keyword(
            "target",
            help_text="The target element to apply the background-image to - this should be a css selector.",
            type_hint="str",
        ),
        Keyword(
            "css_variable_name",
            optional=True,
            help_text="The CSS variable name to apply the background-image to. element.style.setProperty(css_variable_name, url);",
            type_hint="str",
        ),
    )
    js_constructor = "wagtail_fedit.editors.WagtailFeditFuncEditor"
    js_function = "wagtail_fedit.funcs.backgroundImageFunc"

    def render_content(self, parent_context=None):
        return ""
    
    def get_response_data(self, parent_context=None):
        data = super().get_response_data(parent_context)
        image = getattr(self.object, self.field_name, None)
        if not image:
            return data

        filter_spec = self.kwargs.get("filter_spec", None)
        if not filter_spec:
            filter_spec = "original"

        if not isinstance(filter_spec, str):
            filter_spec = "|".join(filter_spec)

        if image.is_svg() or self.kwargs.get("preserve_svg", False):
            filter = Filter(to_svg_safe_spec(filter_spec.split("|")))
        else:
            filter = Filter(spec=filter_spec)

        rendition = get_rendition_or_not_found(
            image,
            filter,
        )

        return data | {
            "url": rendition.url,
            "css_variable_name":\
                self.kwargs.get("css_variable_name", None) or "background-image",
        }
