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
)
from ..settings import (
    SIGN_SHARED_CONTEXT,
)
from ..utils import (
    FeditIFrameMixin,
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


import pickle, json, base64



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

def Base85_json_dumps(obj):
    return base64.b85encode(json.dumps(obj).encode("utf-8")).decode("utf-8")

def Base85_json_loads(data):
    return json.loads(base64.b85decode(data).decode("utf-8"))

class BaseAdapter(FeditIFrameMixin):
    identifier              = None
    signer: Signer          = Signer()
    # Required keyword arguments for the adapter
    required_kwargs         = []
    # Optional keyword arguments for the adapter, these are only used to print the help example.
    optional_kwargs         = []
    # Tokens which should be resolved absolutely (no parser.compile_filter)
    # These are NOT required.
    absolute_tokens         = [
        "inline",
    ]
    # An optional description to be displayed when running the help command.
    usage_description       = "This adapter is used to edit a field of a model instance."
    # A dictionary of help text for the adapter.
    help_text_dict          = {}

    # The JS constructor for the adapter.
    # This will receive the data after a successful form submission.
    js_constructor          = None

    def __init__(self, object: models.Model, field_name: str, request: HttpRequest, **kwargs):
        self.object         = object
        self.field_name     = field_name
        self.meta_field     = object._meta.get_field(field_name)
        self.request        = request
        self.kwargs         = kwargs

    @classmethod
    def get_usage_string(cls) -> str:
        """
        Return a string which describes how to use the adapter.
        """
        s = []
        for i, token in enumerate(cls.absolute_tokens):
            s.append(f"{token}")
            if i < len(cls.absolute_tokens) - 1:
                s.append(" ")
        
        if cls.absolute_tokens and cls.required_kwargs:
            s.append(" ")

        for i, kwarg in enumerate(cls.required_kwargs):
            s.append(f"{kwarg}=value")
            if i < len(cls.required_kwargs) - 1:
                s.append(" ")

        if (
            cls.required_kwargs and cls.optional_kwargs or\
            not cls.required_kwargs and cls.absolute_tokens and cls.optional_kwargs
        ):
            s.append(" ")
        
        for i, kwarg in enumerate(cls.optional_kwargs):
            s.append(f"[{kwarg}=value]")
            if i < len(cls.optional_kwargs) - 1:
                s.append(" ")
                
        return "".join(s)
    
    @classmethod
    def get_usage_description(cls) -> str:
        """
        Return a description of how the adapter is used.
        """
        return cls.usage_description
    
    @classmethod
    def get_usage_help_text(cls) -> list[str]:
        """
        Return a help text which describes how to use the adapter.
        This might be a good time to exalain the kwargs.
        """
        if "inline" in cls.absolute_tokens:
            return {
                "inline": "if passed; the adapter will be rendered with inline styles.",
                **cls.help_text_dict,
            }
        return cls.help_text_dict

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
    
    def get_admin_url(self) -> str:
        """
        Return the admin URL for the object.
        """
        raise NotImplementedError

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
        # return self.signer.sign_object(self.kwargs)# , serializer=PickleBlockSerializer)
        if SIGN_SHARED_CONTEXT:
            return self.signer.sign_object(self.kwargs, compress=True)
        
        return Base85_json_dumps(self.kwargs)

    @classmethod
    def decode_shared_context(cls, request: HttpRequest, object: models.Model, field: str, context: str) -> dict:
        """
        Decode an encoded contex string back to a dictionary.
        """
        if not context:
            return {}
        if SIGN_SHARED_CONTEXT:
            return cls.signer.unsign_object(context)# , serializer=PickleBlockSerializer)
        try:
            return Base85_json_loads(context)
        except json.JSONDecodeError:
            pass
        return {}
    
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

