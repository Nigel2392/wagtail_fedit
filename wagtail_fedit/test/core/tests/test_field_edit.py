from wagtail.models import (
    RevisionMixin,
)
from .base import (
    BaseFEditTest,
)

class TestFieldEdit(BaseFEditTest):
    def test_field_edited(self):
        self.client.force_login(self.admin_user)
        
        for i, model in enumerate(self.models):
            
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

    def test_unauthorized_unchanged(self):
        self.client.force_login(self.regular_user)
        
        for i, (model, has_revision_support) in enumerate([
            (self.full_model, True),
            (self.draft_model, True),
            (self.revision_model, True),
            (self.preview_model, False),
            (self.basic_model, False),
        ]):
            
            initial_title = model.title
            response = self.client.post(
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

            self.assertEqual(response.status_code, 403)

            model.refresh_from_db()

            if has_revision_support:
                self.assertEqual(model.revisions.count(), 0)
                chk = model

            else:
                with self.assertRaises(AttributeError):
                    model.revisions.count()
                chk = model

            self.assertEqual(chk.title, initial_title)
