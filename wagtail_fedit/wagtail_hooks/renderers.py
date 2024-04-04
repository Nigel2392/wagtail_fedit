from wagtail.templatetags.wagtailcore_tags import richtext
from wagtail.fields import RichTextField
from wagtail import hooks

from ..hooks import REGISTER_FIELD_RENDERER


@hooks.register(REGISTER_FIELD_RENDERER)
def register_renderers(renderer_map):
    # This is a custom renderer for RichText fields.
    # It will render the RichText field as a RichText block.
    renderer_map[RichTextField] = lambda request, context, instance, value: richtext(value)

