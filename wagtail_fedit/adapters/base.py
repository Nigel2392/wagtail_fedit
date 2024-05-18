from typing import (
    TYPE_CHECKING, Any, Type,
)
from django import forms
from django.db import models
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property
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
    SHARE_WITH_SESSIONS,
    USE_ADAPTER_SESSION_ID,
    TRACK_LOCALES,
)
from ..utils import (
    FeditIFrameMixin,
    wrap_adapter,
)

if TYPE_CHECKING:
    from ..toolbar import (
        FeditToolbarComponent,
    )

import json, base64, uuid


class AdapterError(Exception):
    pass


def content_id_from_parts(*parts: Any) -> str:
    return "-".join(map(slugify, map(str, parts)))

def Base85_json_dumps(obj):
    return base64.b85encode(json.dumps(obj).encode("utf-8")).decode("utf-8")

def Base85_json_loads(data):
    return json.loads(base64.b85decode(data).decode("utf-8"))

def _get_keywords(bases, attrs):
    if "keywords" in attrs:
        return list(attrs["keywords"])
    
    for base in bases:
        if hasattr(base, "keywords"):
            return list(base.keywords)
        
    return list()

def _sort_keywords(keywords):
    _s = sorted(
        list(set(keywords)),
        key=lambda x: (not x.absolute, x.optional, x.default is not None, x.name)
    )
    return _s



class VARIABLES:
    PY_SIZE_VAR = "editor_size"
    FORM_SIZE_VAR = "data-editor-size"



class Keyword:
    def __init__(self, name: str, optional: bool = False, absolute: bool = False, default=None, help_text: str = None, type_hint: Type[Any] = None):

        if (default and absolute) or (default and not optional):
            raise AdapterError("Keywords cannot be absolute or required and have a default value")

        if optional and absolute:
            raise AdapterError("Keywords cannot be optional and absolute")
        
        if default is not None and not type_hint:
            type_hint = type(default)
        
        self.name = name
        self.optional = optional
        self.absolute = absolute
        self.default = default
        self.help_text = help_text
        self.type_hint = type_hint

    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, Keyword):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        return False

    def __str__(self):
        k = []

        if self.optional:
            k.append("?")
        if self.absolute:
            k.append("!")

        k.append(self.name)

        if self.type_hint and not self.absolute:
            if isinstance(self.type_hint, str):
                k.append(f": {self.type_hint}")
            else:
                k.append(f": {self.type_hint.__name__}")
                
        if self.default is not None and not self.absolute:
            default = self.default
            if isinstance(default, str):
                default = f"'{default}'"
            k.append(f"={default}")

        return "".join(k)

    def __repr__(self):
        s = ["Keyword", self.name]
        if self.optional:
            s.append("optional")
        elif not self.absolute:
            s.append("required")
        if self.absolute:
            s.append("absolute")
        if self.default:
            s.append(f"default={self.default}")
        if self.help_text:
            s.append(f"help_text='{self.help_text}'")
        if self.type_hint:
            s.append(f"type: {self.type_hint}")
        s = " ".join(s)
        return f"<{s}>"

class AdapterMeta(type):
    def __new__(cls, name, bases, attrs):
        keywords: list[Keyword] = _get_keywords(bases, attrs)
        
        required_kwargs = []
        absolute_tokens = []
        _defaults       = {}

        for keyword in keywords:
            if keyword.absolute:
                absolute_tokens.append(keyword.name)
                _defaults[keyword.name] = False
            elif keyword.optional:
                _defaults[keyword.name] = keyword.default
            else:
                required_kwargs.append(keyword.name)

        cls = super().__new__(cls, name, bases, attrs)

        cls.required_kwargs: tuple[str]     = tuple(required_kwargs)
        cls.absolute_tokens: tuple[str]     = tuple(absolute_tokens)
        cls._defaults:       dict[str, Any] = _defaults
        cls.keywords:        tuple[Keyword] = tuple(
            _sort_keywords(keywords)
        )

        return cls


class BaseAdapter(FeditIFrameMixin, metaclass=AdapterMeta):
    # Type hints for keyword arguments set by metaclass.
    required_kwargs: tuple[str]
    absolute_tokens: tuple[str]
    _defaults:       dict[str, Any]

    # How the adapter is identified on inside of the templatetag.
    identifier              = None

    # If the templatetag required the first argument to be model.field or just model
    field_required          = True

    # The template used to render the form.
    template_name           = "wagtail_fedit/editor/adapter_iframe.html"
    editable_template_name  = "wagtail_fedit/content/editable_adapter.html"

    signer: Signer          = Signer()
    
    # Keyword arguments for the adapter
    keywords: tuple[Keyword]     = (
        Keyword(
            "inline",
            absolute=True,
            help_text="if passed; the adapter will be rendered with inline styles."
        ),
    )

    # An optional description to be displayed when running the help command.
    usage_description       = "This adapter is used to edit a field of a model instance."

    # The JS constructor for the adapter.
    # This will receive the data after a successful form submission.
    js_constructor          = None

    def __init__(self, object: models.Model, field_name: str, request: HttpRequest, **kwargs):
        self.object           = object
        self.request          = request
        self.kwargs           = self._defaults.copy() | kwargs

        if hasattr(request, "LANGUAGE_CODE") and TRACK_LOCALES:
            if "LANGUAGE_CODE" not in self.kwargs:
                self.kwargs["LANGUAGE_CODE"] = request.LANGUAGE_CODE

            if self.kwargs["LANGUAGE_CODE"] != request.LANGUAGE_CODE:
                translation.activate(self.kwargs["LANGUAGE_CODE"])

        if self.field_required:
            self.field_name     = field_name
            self.meta_field     = object._meta.get_field(field_name)
        else:
            self.field_name     = None
            self.meta_field     = None

    @classmethod
    def get_usage_string(cls) -> str:
        """
        Return a string which describes how to use the adapter.
        """
        s = []
        for keyword in cls.keywords:
            s.append(str(keyword))
                
        return " ".join(s)
    
    def get_form_context(self, **kwargs):
        return {
            "adapter": self,
            "field_name": self.field_name,
            "meta_field": self.meta_field,
        }

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
        d = {}
        for keyword in cls.keywords:
            if keyword.name not in d:
                d[keyword.name] = keyword.help_text
        return d
    
    def get_template_names(self) -> list[str]:
        """
        Return the template names for the adapter.
        """
        return [self.template_name]
    
    def get_editable_template_names(self) -> list[str]:
        """
        Return the template names for the adapter.
        """
        return [self.editable_template_name]

    @property
    def field_value(self):
        """
        Call the value_from_object method on
        the meta field to get the value from the instance.
        """
        return getattr(self.object, self.field_name)
    
    @cached_property
    def model(self):
        """
        Return the model class of the object.
        """
        return self.object.__class__
    
    @cached_property
    def tooltip(self):
        """
        Return the tooltip for the adapter.
        """
        return self.get_header_title()
    
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

    def get_response_data(self, parent_context) -> dict:
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
    
    def get_element_id_parts(self) -> list[str]:
        """
        Return the parts of the element ID.
        """
        return [
            self.model._meta.app_label,
            self.model._meta.model_name,
            self.object.pk,
            self.field_name,
        ]

    def get_element_id(self) -> str:
        """
        Return a unique identifier for the elements on the frontend.
        """
        return content_id_from_parts(
            *self.get_element_id_parts(),
        )
    
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
        
        if SHARE_WITH_SESSIONS:
            if USE_ADAPTER_SESSION_ID:
                # This ID should be uniquely generated for each adapter instance.
                # But this is not always possible - hence why we allow UUID's.
                id = self.get_element_id()
            else:
                # Set in kwargs, try not to clutter session data too much.
                id = self.kwargs.setdefault(
                    "wagtail_fedit_uuid",
                    str(uuid.uuid4())
                )
                
            self.request.session[id] = self.kwargs
            self.request.session.modified = True
            return id
        
        if SIGN_SHARED_CONTEXT:
            return self.signer.sign_object(
                self.kwargs,
                compress=True,
                # serializer=SharedContextSerializer(
                #     self,
                # ),
            )
        
        return Base85_json_dumps(self.kwargs)


    @classmethod
    def decode_shared_context(cls, request: HttpRequest, object: models.Model, field: str, context: str) -> dict:
        """
        Decode an encoded contex string back to a dictionary.
        """
        if SHARE_WITH_SESSIONS:
            if not context:
                return {}
            return request.session.get(context, {})
        
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
        data = super().get_response_data(parent_context)
        data["html"] = wrap_adapter(
            request=self.request,
            adapter=self,
            context=parent_context,
            run_context_processors=True
        )
        return data

class DomPositionedMixin(BaseAdapter):
    template_name = "wagtail_fedit/editor/adapter_iframe_dom_positioned.html"
    editable_template_name  = "wagtail_fedit/content/editable_dom_positioned_adapter.html"
    js_constructor = "wagtail_fedit.editors.DomPositionedBlockFieldEditor"