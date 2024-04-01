from typing import Any
from django.http import HttpRequest
from django.db import models
from wagtail import hooks

from .hooks import EXCLUDE_FROM_RELATED_FORMS


FEDIT_PREVIEW_VAR = "_wagtail_fedit_preview"
USERBAR_MODEL_VAR = "_wagtail_fedit_userbar_model"


class FeditPermissionCheck:
    @staticmethod
    def has_perms(request: HttpRequest, model: Any) -> bool:
        
        if (
            not request.user.is_authenticated\
            or not request.user.has_perm("wagtailadmin.access_admin")\
            or not request.user.has_perm(f"{model._meta.app_label}.change_{model._meta.model_name}")    
        ):
            return False
        
        return True


def use_related_form(field: models.Field) -> bool:
    for hook in hooks.get_hooks(EXCLUDE_FROM_RELATED_FORMS):
        if hook(field):
            return False
    return True


def access_userbar_model(request: HttpRequest) -> models.Model:

    if not hasattr(request, USERBAR_MODEL_VAR):
        return None
    
    return getattr(request, USERBAR_MODEL_VAR)

def with_userbar_model(request: HttpRequest, model: models.Model) -> HttpRequest:
    setattr(request, USERBAR_MODEL_VAR, model)
    return request
