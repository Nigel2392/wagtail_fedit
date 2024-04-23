from django.utils.html import format_html
from django.templatetags.static import static
from wagtail import hooks
from wagtail.models import Page
from wagtail.admin.widgets import (
    AdminPageChooser,
)
from wagtail.fields import (
    RichTextField,
    StreamField,
)
from wagtail.templatetags.wagtailcore_tags import (
    richtext,
)
from wagtail.images import (
    get_image_model,
)
from wagtail.images.widgets import AdminImageChooser
from wagtail.documents import get_document_model
from wagtail.documents.widgets import AdminDocumentChooser
from ..hooks import (
    EXCLUDE_FROM_RELATED_FORMS,
    REGISTER_FIELD_RENDERER,
    REGISTER_FIELD_WIDGETS,
    FIELD_EDITOR_SIZE,
    REGISTER_CSS,
    REGISTER_JS,
)

Image = get_image_model()
Document = get_document_model()

@hooks.register(EXCLUDE_FROM_RELATED_FORMS)
def exclude_related_forms(field):
    if field.related_model in [Page, Image, Document]:
        return True
    return False


@hooks.register(REGISTER_FIELD_RENDERER)
def register_renderers(renderer_map):
    # This is a custom renderer for RichText fields.
    # It will render the RichText field as a RichText block.
    renderer_map[RichTextField] = lambda request, context, instance, value: richtext(value)

@hooks.register(REGISTER_FIELD_WIDGETS)
def register_field_widgets(widgets):
    widgets[Image] = AdminImageChooser
    widgets[Document] = AdminDocumentChooser
    widgets[Page] = AdminPageChooser
    return widgets

@hooks.register(FIELD_EDITOR_SIZE)
def field_editor_size(model_instance, model_field):
    if isinstance(model_field, RichTextField):
        return "large"
    
    if isinstance(model_field, StreamField):
        return "full"
    
    return None


# <link rel="stylesheet" href="{% static 'wagtail_fedit/css/frontend.css' %}">
# <script src="{% static 'wagtail_fedit/js/frontend.js' %}"></script>

@hooks.register(REGISTER_CSS, order=-1)
def register_css(request):
    return [
        format_html(
            '<link rel="stylesheet" href="{0}">',
            static('wagtail_fedit/css/frontend.css')
        ),
    ]

@hooks.register(REGISTER_JS, order=-1)
def register_js(request):
    return [
        format_html(
            '<script src="{0}"></script>',
            static('wagtail_fedit/vendor/tippy/popper.min.js')
        ),
        format_html(
            '<script src="{0}"></script>',
            static('wagtail_fedit/vendor/tippy/tippy-bundle.min.js')
        ),
        format_html(
            '<script src="{0}"></script>',
            static('wagtail_fedit/js/frontend.js')
        ),
    ]
