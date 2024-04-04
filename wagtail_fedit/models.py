from typing import Type
from wagtail.permission_policies import ModelPermissionPolicy
from wagtail.models import (
    RevisionMixin,
    PreviewableMixin,
    DraftStateMixin,
    WorkflowMixin,
    LockableMixin,
)


class FEditableMixin(DraftStateMixin, RevisionMixin, PreviewableMixin):

    class Meta:
        abstract = True

    def get_admin_display_title(self):
        return getattr(self, "title", str(self))
    
    def get_url(self, request):
        raise NotImplementedError("get_url must be implemented by subclasses; it should return the URL of the object on the frontend site.")
    
    def get_permissions_policy(self):
        return ModelPermissionPolicy(self.__class__)
    
    def permissions_for_user(self, user):
        return FeditPermissionTester(
            model=self,
            user=user,
            policy=self.get_permissions_policy()
        )


class FeditPermissionTester:
    model: Type[FEditableMixin]
    
    def __init__(self, model_instance, user, policy = Type[ModelPermissionPolicy]):
        self.user = user
        self.model = model_instance.__class__
        self.policy: ModelPermissionPolicy = policy(model=self.model)
        self.model_instance: FEditableMixin = model_instance

        # From wagtail.models.PagePermissionTester.__init__
        if self.user.is_active and not self.user.is_superuser:
            self.permissions = {
                # Get the 'action' part of the permission codename, e.g.
                # 'add' instead of 'add_page'
                perm.permission.codename.rsplit("_", maxsplit=1)[0]
                for perm in self.policy.get_cached_permissions_for_user(user)
            }

    def is_live(self):
        return self.model_instance.live
    
    def is_root(self):
        if hasattr(self.model_instance, "is_root"):
            return self.model_instance.is_root()
        return False
    
    def is_locked(self):
        if isinstance(self.model_instance, LockableMixin):
            return self.model_instance.locked
        return False

    def can_unpublish(self):
        # From wagtail.models.PagePermissionTester.can_unpublish
        if not self.user.is_active:
            return False
        
        if (not self.is_live()) or self.is_root():
            return False
        
        if self.is_locked():
            return False

        return self.user.is_superuser or ("publish" in self.permissions)

    def can_publish(self):
        # From wagtail.models.PagePermissionTester.can_publish
        if not self.user.is_active:
            return False

        if self.is_root():
            return False

        return self.user.is_superuser or ("publish" in self.permissions)
    
    def can_submit_for_moderation(self):
        if not isinstance(self.model_instance, LockableMixin):
            return False
        
        if not isinstance(self.model_instance, WorkflowMixin):
            return False

        return (
            not self.is_locked()
            and self.model_instance.has_workflow
            and not self.model_instance.workflow_in_progress
        )
