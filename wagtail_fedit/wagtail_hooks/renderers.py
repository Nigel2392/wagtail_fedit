from wagtail.templatetags.wagtailcore_tags import richtext
from wagtail.rich_text import RichText
from wagtail import hooks

from .hooks import REGISTER_TYPE_RENDERER


@hooks.register(REGISTER_TYPE_RENDERER)
def register_renderers(renderer_map):
    # This is a custom renderer for RichText fields.
    # It will render the RichText field as a RichText block.
    renderer_map[RichText] = lambda request, context, value: richtext(value)

