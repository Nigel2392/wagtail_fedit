from wagtail.models import (
    RevisionMixin,
)
from .base import (
    BaseFEditTest,
)

import json

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
        
        for i, model in enumerate(self.models):
            
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

            self.assertEqual(response.status_code, 403, msg=f"Expected 403, got {response.status_code} ({response.content})")

            model.refresh_from_db()

            if isinstance(model, RevisionMixin):
                self.assertEqual(model.revisions.count(), 0)
                chk = model

            else:
                with self.assertRaises(AttributeError):
                    model.revisions.count()
                chk = model

            self.assertEqual(chk.title, initial_title)


    def test_lock_unchanged(self):
        self.client.force_login(self.other_admin_user)
        initial_content = self.lock_model.title

        response = self.client.post(
            self.get_field_url(
                "title",
                self.lock_model._meta.app_label,
                self.lock_model._meta.model_name,
                self.lock_model.pk,
            ),
            {
                "title": f"{self.lock_model.title} test case"
            }
        )

        self.lock_model.refresh_from_db()

        self.assertEqual(response.status_code, 423) # 423 Locked
        self.assertEqual(self.lock_model.revisions.count(), 0)
        
        try:
            response_content = (json.loads(response.content) or {})
        except json.JSONDecodeError:
            self.fail("Response content is not valid JSON")
            
        self.assertTrue(response_content.get("locked", False))
        self.assertEqual(self.lock_model.locked_by, self.admin_user)
        self.assertEqual(self.lock_model.title, initial_content)
        

