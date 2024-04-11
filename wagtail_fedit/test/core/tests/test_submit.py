from django.contrib.contenttypes.models import (
    ContentType,
)
from wagtail.models import (
    Workflow,
    WorkflowTask,
    WorkflowContentType,
    GroupApprovalTask,
)
from .base import (
    BaseFEditTest,
)
from wagtail_fedit.views import (
    PublishView,
    SubmitView,
    UnpublishView,
    CancelView,
)


class TestSubmitViews(BaseFEditTest):

    def makeRequest(self, url_name: str, model, view_class, check_status = 0):
        url = self.get_url_for(url_name,
            app_label=model._meta.app_label,
            model_name=model._meta.model_name,
            model_id=model.pk,
        )
        view = view_class()
        view.request = self.request_factory.post(url)
        expected_post_value = view.get_action_value()

        response = self.client.post(url, {"action": expected_post_value})
        if check_status:
            self.assertEqual(response.status_code, check_status, msg=f"Request failed for {url_name}")
        return response

    def test_publish(self):
        self.client.force_login(self.admin_user)
        
        self.full_model.unpublish()

        self.assertFalse(self.full_model.live)

        self.makeRequest("publish", self.full_model, PublishView, 302)

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

        self.makeRequest("unpublish", self.full_model, UnpublishView, 302)

        self.full_model.refresh_from_db()

        self.assertFalse(self.full_model.live)

    def test_submit(self):
        self.client.force_login(self.admin_user)
        
        self.full_model.has_unpublished_changes = True
        self.full_model.save()

        workflow = self.full_model.get_workflow()
        self.assertIsNone(workflow)

        workflow = Workflow.objects.get_or_create(name="test_workflow")[0]
        workflow_task = GroupApprovalTask.objects.create(name="test_task_1")
        content_type = ContentType.objects.get_for_model(self.full_model.__class__)
        WorkflowContentType.objects.create(content_type=content_type, workflow=workflow)
        WorkflowTask.objects.create(
            workflow=workflow, task=workflow_task, sort_order=1
        )

        wf = self.full_model.get_workflow()
        self.assertIsNotNone(wf)
        self.assertEqual(wf, workflow)
        self.assertFalse(not not self.full_model.workflow_states.all())

        self.makeRequest("submit", self.full_model, SubmitView, 302)

        self.full_model = self.full_model.__class__.objects.get(pk=self.full_model.pk)
        workflow: Workflow = self.full_model.get_workflow()
        current_state = self.full_model.current_workflow_state

        self.assertEqual(
            current_state.status,
            current_state.STATUS_IN_PROGRESS,
        )

    def test_cancel(self):
        self.test_submit()

        self.makeRequest("cancel", self.full_model, CancelView, 302)

        self.full_model.refresh_from_db()

        current_state = self.full_model.workflow_states.first()
        self.assertEqual(
            current_state.status,
            current_state.STATUS_CANCELLED,
        )

    def test_lock_nopublish(self):
        self.client.force_login(self.other_admin_user)
        
        self.lock_model.live = False
        self.lock_model.has_unpublished_changes = True
        self.lock_model.save(update_fields=["live", "has_unpublished_changes"])

        self.makeRequest("publish", self.lock_model, PublishView, 200)

        self.lock_model.refresh_from_db()

        self.assertFalse(self.lock_model.live)
        self.assertTrue(self.lock_model.has_unpublished_changes)

    def test_lock_nounpublish(self):
        self.client.force_login(self.admin_user)

        if not self.lock_model.latest_revision:
            self.lock_model.save_revision(
                user=self.admin_user,
                clean=False,
            )

        self.lock_model.publish(
            user=self.admin_user,
            revision=self.lock_model.latest_revision,
        )
        
        self.makeRequest("unpublish", self.lock_model, UnpublishView, 200)

        self.lock_model.refresh_from_db()

        self.assertTrue(self.lock_model.live)
        self.assertFalse(self.lock_model.has_unpublished_changes)

    def test_lock_nosubmit(self):
        self.client.force_login(self.admin_user)
        
        self.makeRequest("submit", self.lock_model, SubmitView, 200)

        self.lock_model.refresh_from_db()

        self.assertTrue(self.lock_model.has_unpublished_changes)
        self.assertFalse(not not self.lock_model.workflow_states)

    def test_lock_nocancel(self):
        self.lock_model.locked = False
        self.lock_model.locked_by = None
        self.lock_model.save(update_fields=["locked", "locked_by"])

        self.test_submit()

        self.lock_model.locked = True
        self.lock_model.locked_by = self.other_admin_user
        self.lock_model.save(update_fields=["locked", "locked_by"])
        
        self.makeRequest("cancel", self.lock_model, CancelView, 200)

        self.lock_model.refresh_from_db()
        current_state = self.full_model.current_workflow_state

        self.assertEqual(
            current_state.status,
            current_state.STATUS_IN_PROGRESS,
        )
