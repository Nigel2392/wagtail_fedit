from django.contrib.contenttypes.models import (
    ContentType,
)
from wagtail.models import (
    Workflow,
    WorkflowContentType,
)
from .base import (
    BaseFEditTest,
)
from wagtail_fedit.views import (
    PublishView,
    SubmitView,
    UnpublishView,
    # CancelView,
)


class TestSubmitViews(BaseFEditTest):

    def makeRequest(self, url_name: str, model, view_class):
        url = self.get_url_for(url_name,
            app_label=model._meta.app_label,
            model_name=model._meta.model_name,
            model_id=model.pk,
        )
        view = view_class()
        view.request = self.request_factory.post(url)
        expected_post_value = view.get_action_value()

        response = self.client.post(url, {"action": expected_post_value})
        self.assertEqual(response.status_code, 302, msg=f"Request failed for {url_name}")
        return response

    def test_publish(self):
        self.client.force_login(self.admin_user)
        
        self.full_model.unpublish()

        self.assertFalse(self.full_model.live)

        self.makeRequest("publish", self.full_model, PublishView)

        self.full_model.refresh_from_db()

        self.assertTrue(self.full_model.live)

    def test_unpublish(self):
        self.client.force_login(self.admin_user)

        revision = self.full_model.save_revision(
            user=self.admin_user,
            clean=False,
        )
        
        self.full_model.publish(
            user=self.admin_user,
            revision=revision,
        )

        self.assertTrue(self.full_model.live)

        self.makeRequest("unpublish", self.full_model, UnpublishView)

        self.full_model.refresh_from_db()

        self.assertFalse(self.full_model.live)

    def test_submit(self):
        self.client.force_login(self.admin_user)
        
        self.full_model.has_unpublished_changes = True
        self.full_model.save()

        workflow = self.full_model.get_workflow()
        self.assertIsNone(workflow)

        workflow = Workflow.objects.create(name="test_workflow")
        content_type = ContentType.objects.get_for_model(self.full_model.__class__)
        WorkflowContentType.objects.create(content_type=content_type, workflow=workflow)

        wf = self.full_model.get_workflow()
        self.assertIsNotNone(wf)
        self.assertEqual(wf, workflow)
        self.assertFalse(not not self.full_model.workflow_states)

        self.makeRequest("submit", self.full_model, SubmitView)

        self.full_model.refresh_from_db()
        workflow: Workflow = self.full_model.get_workflow()
        self.assertTrue(not not self.full_model.workflow_states)
        