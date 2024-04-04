from wagtail import hooks
from wagtail.models import Page
from wagtail.images.models import Image
from wagtail.documents.models import Document
from ..hooks import (
    EXCLUDE_FROM_RELATED_FORMS,
)

@hooks.register(EXCLUDE_FROM_RELATED_FORMS)
def exclude_related_forms(field):
    if field.related_model in [Page, Image, Document]:
        return True
    return False


