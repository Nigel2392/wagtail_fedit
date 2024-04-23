from django.forms.models import model_to_dict
from wagtail.admin.panels import (
    FieldPanel,
    ObjectList,
)
from wagtail.models import (
    RevisionMixin,
)
from .base import (
    BaseFEditTest,
)

import json

class TestModelEdit(BaseFEditTest):
    def test_model_edited(self):
        self.client.force_login(self.admin_user)
        
        for i, model in enumerate(self.models):
            
            if isinstance(model, RevisionMixin):
                self.assertEqual(model.revisions.count(), 0)
            else:
                with self.assertRaises(AttributeError):
                    model.revisions.count()

            panels = [
                FieldPanel("title"),
                FieldPanel("body"),
            ]

            setattr(model.__class__, "panels", panels)
            setattr(model.__class__, "edit_handler", ObjectList(panels))

            initial_title = model.title
            d = model_to_dict(model, fields=["title", "body"])
            d["title"] = f"{model.title} test case {i + 1}"

            self.client.post(
                self.get_model_url(
                    model._meta.app_label,
                    model._meta.model_name,
                    model.pk,
                ),
                d,
            )

            model.refresh_from_db()

            if isinstance(model, RevisionMixin):
                self.assertEqual(model.revisions.count(), 1, msg=f"Expected 1 revision, got {model.revisions.count()} for {model.__class__.__name__} '{model}'")
                self.assertEqual(model.title, initial_title, msg=f"Expected title to be '{initial_title}', got '{model.title}' for {model.__class__.__name__} '{model}'")
                chk = model.latest_revision.as_object()
            else:
                with self.assertRaises(AttributeError):
                    model.revisions.count()
                chk = model

            chk_title = f"{initial_title} test case {i + 1}"
            self.assertEqual(chk.title, chk_title, msg=f"Expected title to be '{chk_title}', got '{chk.title}' for {model.__class__.__name__} '{model}'")

    def test_unauthorized_unchanged(self):
        self.client.force_login(self.regular_user)
        
        for i, model in enumerate(self.models):
            
            initial_title = model.title
            model.__class__.panels = [
                FieldPanel("title"),
                FieldPanel("body"),
            ]
            model.__class__.edit_handler = ObjectList(model.__class__.panels)
            d = model_to_dict(model, fields=["title", "body"])
            d["title"] = f"{model.title} test case {i + 1}"
            response = self.client.post(
                self.get_model_url(
                    model._meta.app_label,
                    model._meta.model_name,
                    model.pk,
                ),
                d,
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
        initial_title = self.lock_model.title

        panels = self.lock_model.__class__.panels
        self.lock_model.__class__.panels = [
            FieldPanel("title"),
            FieldPanel("body"),
        ]

        d = model_to_dict(self.lock_model, fields=["title", "body"])
        d["title"] = f"{self.lock_model.title} test case"

        response = self.client.post(
            self.get_model_url(
                self.lock_model._meta.app_label,
                self.lock_model._meta.model_name,
                self.lock_model.pk,
            ),
        )

        self.lock_model.__class__.panels = panels
        self.lock_model.refresh_from_db()

        self.assertEqual(response.status_code, 423, msg=str(response.content)) # 423 Locked
        self.assertEqual(self.lock_model.revisions.count(), 0)
        
        try:
            response_content = (json.loads(response.content) or {})
        except json.JSONDecodeError:
            self.fail("Response content is not valid JSON")
            
        self.assertTrue(response_content.get("locked", False))
        self.assertEqual(self.lock_model.locked_by, self.admin_user)
        self.assertEqual(self.lock_model.title, initial_title)

        
        

