from typing import (
    Optional, Any,
)
from django import forms
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import (
    slugify,
)
from django.core.signing import (
    Signer,
)
from django.http import (
    HttpRequest,
    HttpResponse,
)

from ..utils import (
    FeditIFrameMixin,
)


class AdapterError(Exception):
    pass


def content_id_from_parts(*parts: Any) -> str:
    return "-".join(map(slugify, map(str, parts)))


import pickle




class PickleBlockSerializer:
    """
    Simple wrapper around pickle to be used in signing.dumps and
    signing.loads.
    """

    def dumps(self, obj):
        return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

    def loads(self, data):
        return pickle.loads(data)


class BaseAdapter(FeditIFrameMixin):
    identifier              = None
    signer                  = Signer()
    # wrapper_template        = None
    # run_context_processors  = True
    required_kwargs         = []

    def __init__(self, object: models.Model, field_name: str, request: HttpRequest, **kwargs):
        self.object         = object
        self.field_name     = field_name
        self.meta_field     = object._meta.get_field(field_name)
        self.request        = request
        self.kwargs         = kwargs

    @property
    def field_value(self):
        return self.meta_field.value_from_object(self.object)
    
    @property
    def model(self):
        return self.object.__class__
    
    def check_permissions(self):
        if not self.request.user.is_authenticated:
            return False
        return True
    
    def get_form(self) -> "forms.Form":
        raise NotImplementedError

    def form_valid(self, form: "forms.Form"):
        pass
    
    def form_invalid(self, form: "forms.Form"):
        pass

    @classmethod
    def render_from_kwargs(cls, context, **kwargs):
        """
        Render the content for the field from the kwargs if possible.
        This should NOT include the wagtail-fedit wrapper.
        This is rendered if anything goes wrong;
        like the model/field variables not being available.
        """
        raise AdapterError("Cannot render {} from kwargs".format(cls.__name__))

    def render_content(self, parent_context: dict = None) -> str:
        """
        Render the content for the field.
        This should NOT include the wagtail-fedit wrapper.
        """
        raise NotImplementedError
    
    def encode_shared_context(self) -> dict:
        if not self.kwargs:
            return ""
        return self.signer.sign_object(self.kwargs)# , serializer=PickleBlockSerializer)

    @classmethod
    def decode_shared_context(cls, context: str) -> dict:
        if not context:
            return {}
        return cls.signer.unsign_object(context)# , serializer=PickleBlockSerializer)
#     
#     def get_wrapper_template(self) -> str:
#         return self.wrapper_template
#     
#     def get_wrapper_context(self, parent_context: dict = None) -> dict:
#         return {
#             "adapter": self,
#             "request": self.request,
#             "wagtail_fedit_field": self.field_name,
#             "wagtail_fedit_instance": self.object,
#             "parent_context": parent_context,
#             **self.kwargs,
#         }
# 
#     def render_wrapped(self, parent_context: dict = None):
#         """
#         Render the output for the field.
#         This should INCLUDE the wagtail-fedit wrapper.
#         """
# 
#         template = self.get_wrapper_template()
#         context = self.get_wrapper_context(parent_context)
#         content = self.render_content()
#         context["content"] = content
# 
#         if self.run_context_processors:
#             return render_to_string(
#                 template,
#                 context,
#                 request=self.request
#             )
#         
#         return render_to_string(
#             template,
#             context
#         )
