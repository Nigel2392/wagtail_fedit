from wagtail.models import (
    RevisionMixin,
)
from wagtail_fedit.utils import (
    find_block,
)
from .base import (
    BaseFEditTest,
)

class TestBlockEdit(BaseFEditTest):
    def test_block_edited(self):
        self.client.force_login(self.admin_user)

        BLOCK_ID = "c757f54d-0df5-4b35-8a06-4174f180ec41"
        
        for i, model in self.models:
            
            if isinstance(model, RevisionMixin):
                self.assertEqual(model.revisions.count(), 0)
            else:
                with self.assertRaises(AttributeError):
                    model.revisions.count()

            bound, _ = find_block(block_id=BLOCK_ID, field=model.content)
            initial_content = bound.value["link"]["text"]

            response = self.client.post(
                self.get_block_url(
                    BLOCK_ID,
                    "content",
                    model._meta.app_label,
                    model._meta.model_name,
                    model.pk,
                ),
                {
                    "value-link-text": f"{initial_content} test case {i + 1}"
                }
            )

            self.assertEqual(response.status_code, 200)
            model.refresh_from_db()

            if isinstance(model, RevisionMixin):
                self.assertEqual(model.revisions.count(), 1)
                chk = model.latest_revision.as_object()
            else:
                with self.assertRaises(AttributeError):
                    model.revisions.count()
                chk = model

            bound, contentpath = find_block(block_id=BLOCK_ID, field=chk.content)
            self.assertEqual(bound.value["link"]["text"], f"{initial_content} test case {i + 1}",
                msg=f"Block: {bound.block} does not contain the expected value: {initial_content} test case {i + 1}"
            )

    def test_unauthorized_unchanged(self):
        self.client.force_login(self.regular_user)
        
        for i, (model, has_revision_support) in enumerate([
            (self.full_model, True),
            (self.draft_model, True),
            (self.revision_model, True),
            (self.preview_model, False),
            (self.basic_model, False),
        ]):
            
            initial_content = model.content
            response = self.client.post(
                self.get_field_url(
                    "content",
                    model._meta.app_label,
                    model._meta.model_name,
                    model.pk,
                ),
                {
                    "content": f"{model.content} test case {i + 1}"
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

            self.assertEqual(chk.content.get_prep_value(), initial_content.get_prep_value())
