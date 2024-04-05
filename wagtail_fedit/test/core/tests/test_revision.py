from wagtail.models import (
    RevisionMixin,
)
from ..models import (
    EditableFullModel,
    EditableDraftModel,
    EditableRevisionModel,
    EditablePreviewModel,
)

from .base import (
    BaseFEditTest,
)

class TestRevisions(BaseFEditTest):
    def test_revision_creation(self):
        self.client.force_login(self.admin_user)
        
        for i, model in self.models:
            
            if isinstance(model, RevisionMixin):
                self.assertEqual(model.revisions.count(), 0)
            else:
                with self.assertRaises(AttributeError):
                    model.revisions.count()

            initial_title = model.title

            self.client.post(
                self.get_field_url(
                    "title",
                    model._meta.app_label,
                    model._meta.model_name,
                    model.pk,
                ),
                {
                    "title": f"{model.title} test case {i + 1}"
                }
            )

            model.refresh_from_db()

            if isinstance(model, RevisionMixin):
                self.assertEqual(model.revisions.count(), 1)
                self.assertEqual(model.title, initial_title)
                chk = model.latest_revision.as_object()
            else:
                with self.assertRaises(AttributeError):
                    model.revisions.count()
                chk = model

            self.assertEqual(chk.title, f"{initial_title} test case {i + 1}")



