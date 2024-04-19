from typing import (
    TYPE_CHECKING, Any,
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
from ..utils import (
    wrap_adapter,
)

if TYPE_CHECKING:
    from ..toolbar import (
        FeditToolbarComponent,
    )

class AdapterError(Exception):
    pass


def content_id_from_parts(*parts: Any) -> str:
    return "-".join(map(slugify, map(str, parts)))


import pickle



class VARIABLES:
    PY_SIZE_VAR = "editor_size"
    FORM_SIZE_VAR = "data-editor-size"


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
    required_kwargs         = [] # Required keyword arguments for the adapter
    absolute_tokens         = [] # Tokens which should be resolved absolutely (no parser.compile_filter)
    js_constructor          = None

    def __init__(self, object: models.Model, field_name: str, request: HttpRequest, **kwargs):
        self.object         = object
        self.field_name     = field_name
        self.meta_field     = object._meta.get_field(field_name)
        self.request        = request
        self.kwargs         = kwargs

    @property
    def field_value(self):
        """
        Call the value_from_object method on
        the meta field to get the value from the instance.
        """
        return self.meta_field.value_from_object(self.object)
    
    @property
    def model(self):
        """
        Return the model class of the object.
        """
        return self.object.__class__
    
    def check_permissions(self):
        """
        Check if the user has the required permissions to edit the field.
        If false; the field will be rendered as normal (read only).
        """
        if not self.request.user.is_authenticated:
            return False
        return True
        
    def get_js_constructor(self) -> str:
        """
        Return the JS constructor for the adapter.
        This is used to link actions from the adapter to the frontend.
        """
        if not self.js_constructor:
            raise AdapterError("No JS constructor defined")
        
        return self.js_constructor

    def get_response_data(self) -> dict:
        """
        The data which is returned to the frontend on a successful form submission.
        """
        return {
            "adapter": {
                "identifier":   self.identifier,
                "constructor":  self.get_js_constructor(),
                "element_id":   self.get_element_id(),
                "model": {
                    "pk":           self.object.pk,
                    "app_label":    self.model._meta.app_label,
                    "model_name":   self.model._meta.model_name,
                },
            }
        }

    def get_toolbar_buttons(self) -> list["FeditToolbarComponent"]:
        """
        Extra possible toolbar buttons.
        This is where for example; the edit icon goes.
        """
        return []

    def get_element_id(self) -> str:
        """
        Return a unique identifier for the elements on the frontend.
        """
        raise NotImplementedError
    
    def get_form_attrs(self) -> dict:
        """
        Extra possible form attributes rendered in the iFrame.
        """
        return {}
    
    def get_form(self) -> "forms.Form":
        """
        Return the form which knows how to handle this datatype.
        """
        raise NotImplementedError

    def form_valid(self, form: "forms.Form"):
        """
        Called if the form is valid; useful for saving the form or other things.
        """
        pass
    
    def form_invalid(self, form: "forms.Form"):
        """
        Called if the form is not valid.
        """
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
        """
        Encode a dictionary to a string.
        This will be passed as a GET parameter to the iFrame.
        Make sure the data is not too large.
        """
        if not self.kwargs:
            return ""
        return self.signer.sign_object(self.kwargs)# , serializer=PickleBlockSerializer)

    @classmethod
    def decode_shared_context(cls, context: str) -> dict:
        """
        Decode an encoded contex string back to a dictionary.
        """
        if not context:
            return {}
        return cls.signer.unsign_object(context)# , serializer=PickleBlockSerializer)

    
class BlockFieldReplacementAdapter(BaseAdapter):
    js_constructor = "wagtail_fedit.editors.BlockFieldEditor"

    def get_response_data(self, parent_context = None):
        data = super().get_response_data()
        data["html"] = wrap_adapter(
            request=self.request,
            adapter=self,
            context=parent_context,
            run_context_processors=True
        )
        return data

