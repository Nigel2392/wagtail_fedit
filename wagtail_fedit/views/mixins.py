from typing import Any
from django.utils import translation
from django.apps import apps
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    HttpResponse,
)
from ..utils import (
    lock_info,
)




class ObjectViewMixin:
    def setup(self, request: HttpRequest, object_id: Any, app_label: str, model_name: str) -> HttpResponse:
        super().setup(request, object_id, app_label, model_name)
        try:
            self.model = apps.get_model(app_label, model_name)
            self.object = self.model._default_manager.get(pk=object_id)
            self.error_response = None
        except (LookupError):
            self.error_response = HttpResponseBadRequest("Invalid model provided")
        except (self.model.DoesNotExist):
            self.error_response = HttpResponseBadRequest("Model not found")


    def dispatch(self, request: HttpRequest, object_id: Any, app_label: str, model_name: str) -> HttpResponse:
        if self.error_response:
            return self.error_response

        return super().dispatch(request, object_id, app_label, model_name)


class LockViewMixin:
    def setup(self, request: HttpRequest, object_id: Any, app_label: str, model_name: str) -> HttpResponse:
        super().setup(request, object_id, app_label, model_name)

        self.lock, self.locked_for_user = lock_info(
            self.object, request.user,
        )


class LocaleMixin:
    def setup(self, *args, **kwargs) -> None:
        super().setup(*args, **kwargs)
        self.setup_locale(self.object)

    @staticmethod
    def setup_locale(object):
        if hasattr(object, "get_locale"):
            locale = object.get_locale()
        elif hasattr(object, "locale"):
            locale = object.locale
        else:
            locale = None

        if locale:
            translation.activate(locale.language_code)
