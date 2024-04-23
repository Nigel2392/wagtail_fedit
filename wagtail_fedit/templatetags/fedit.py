from typing import Type, Any
from django.template import (
    library, Node, TemplateSyntaxError,
)
from django.template.context import (
    Context,
)
from django.template.base import (
    Parser, Token,
    FilterExpression,
)
from django.http import HttpRequest
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.core import signing

from wagtail import hooks

import warnings

from ..adapters import (
    adapter_registry,
    RegistryLookUpError,
    BaseAdapter,
    AdapterError,
)
from ..utils import (
    wrap_adapter,
    _can_edit,
    FEDIT_PREVIEW_VAR,
    TEMPLATE_TAG_NAME,
)
from ..hooks import (
    REGISTER_CSS,
    REGISTER_JS,
)


register = library.Library()


WARNING_FIELD_NAME_NOT_AVAILABLE = "Field name is not available in the context for %(object)s."
WARNING_MODEL_INSTANCE_NOT_AVAILABLE = "Model instance is not available in the context for %(object)s."


def as_var(var: str, context: Context, value: str) -> str:
    if not var:
        return value

    context[var] = value
    return ""

class AdapterNode(Node):
    signer = signing.TimestampSigner()

    def __init__(self, adapter: Type[BaseAdapter], model: FilterExpression, getters: list[str], as_var: str = None, **kwargs):
        self.adapter = adapter
        self.model = model
        self.getters = getters
        self.kwargs = kwargs
        self.as_var = as_var

    def _resolve_expressions(self, context, model, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, FilterExpression):
                kwargs[k] = v.resolve(context)
        
        if isinstance(model, FilterExpression):
            model = model.resolve(context)

        return model, kwargs

    def render(self, context):
        model = self.model
        getters = self.getters

        model, kwargs = self._resolve_expressions(
            context, model, **self.kwargs,
        )

        if "wagtail_fedit_field" in context\
            and "wagtail_fedit_instance" in context\
            and not model and self.adapter.field_required:

            field_name = context["wagtail_fedit_field"]
            obj = context["wagtail_fedit_instance"]

        elif not model and "wagtail_fedit_instance" in context and not self.adapter.field_required:
            obj = context["wagtail_fedit_instance"]
            field_name = None
            
        else:

            if not model:
                warnings.warn(
                    WARNING_MODEL_INSTANCE_NOT_AVAILABLE % {
                        "object": self.adapter.__name__,
                    },
                    RuntimeWarning,
                )

                context = context.flatten()

                try:
                    return as_var(self.as_var, context, self.adapter.render_from_kwargs(
                        context, **kwargs,
                    ))
                except AdapterError as e:
                    raise TemplateSyntaxError(str(e))

            field_name = None
            obj = model
            if getters:
                field_name = getters[len(getters) - 1]

                for i in range(len(getters) - 1):
                    getter = getters[i]
                    try:
                        obj = getattr(obj, getter)
                    except AttributeError:
                        raise AttributeError(f"Object {model.__class__.__name__} does not have attribute {getter}")
                    

        request = context.get("request")
        adapter = self.adapter(
            object=obj,
            field_name=field_name,
            request=request,
            **kwargs,
        )

        if not adapter.check_permissions()\
          or not _can_edit(request, obj):
            context.update(adapter.kwargs)
            return as_var(self.as_var, context, adapter.render_content(context))

        return as_var(self.as_var, context, wrap_adapter(request, adapter, context))


@register.tag(name=TEMPLATE_TAG_NAME)
def do_render_fedit(parser: Parser, token: Token):

    tokens = token.split_contents()

    _ = tokens.pop(0)
    adapter_id = tokens.pop(0)

    try:
        adapter = adapter_registry[adapter_id]
    except RegistryLookUpError:
        raise TemplateSyntaxError(f"No adapter found with identifier '{adapter_id}'")

    model, model_tokens = None, None
    if tokens:
        model__field = tokens.pop(0)
        model_tokens = model__field.split(".")
        
        # If the field is required; the length must be at least 2,
        # or the first token must be "from_context"
        if len(model_tokens) < 2:
            if model_tokens[0] != "from_context" and adapter.field_required:
                raise TemplateSyntaxError(
                    "Model and field name are required: 'mymodel.myfield' or 'from_context'",
                )

        # If the field is not required; the length could be 1 by specifying only a model.
        if len(model_tokens) > 1 or (
            model_tokens[0] != "from_context" and not adapter.field_required
        ):
            # mymodel
            # mymodel.myfield
            # mymodel.related_field.myfield
            model = parser.compile_filter(model_tokens.pop(0))

    as_var = None
    if tokens and tokens[len(tokens)-2] == "as":
        as_var = tokens.pop(len(tokens)-1)
        tokens.pop(len(tokens)-1)

    kwargs = get_kwargs(
        parser,
        tokens,
        adapter.required_kwargs,
        adapter.absolute_tokens,
        adapter.optional_kwargs,
    )

    return AdapterNode(
        adapter=adapter,
        model=model,
        getters=model_tokens,
        as_var=as_var,
        **kwargs,
    )



@register.simple_tag(takes_context=True)
def render_adapter(context: Context, adapter: BaseAdapter) -> str:
    parent_context = {}
    
    if "parent_context" in context:
        parent_context = context["parent_context"]
        del context["parent_context"]

    context.update(parent_context)

    context["wagtail_fedit_field"]    = adapter.field_name
    context["wagtail_fedit_instance"] = adapter.object
    context["request"]                = adapter.request

    context.update(adapter.kwargs)

    return adapter.render_content(context)


@register.inclusion_tag("wagtail_fedit/_hook_output.html", name="fedit_scripts", takes_context=True)
def static_hook_output(context, css_or_js) -> dict:
    css_or_js = css_or_js.lower()

    if css_or_js not in ["css", "js"]:
        raise ValueError("Invalid argument, must be 'css' or 'js'")

    request = context.get("request")
    
    if css_or_js == "css":
        hook_name = REGISTER_CSS
    else:
        hook_name = REGISTER_JS

    if not getattr(request, FEDIT_PREVIEW_VAR, False):
        return {}

    files = []
    for hook in hooks.get_hooks(hook_name):
        ret = hook(request)
        
        if not isinstance(ret, (list, tuple)):
            ret = [ret]

        files.extend(ret)
        
    return {
        "hook_output": files,
    }

@register.simple_tag(takes_context=False, name="tooltip")
def tooltip(content, wrapping: str = None, **kwargs) -> str:
    kwargs["content"] = content
    s = [
        "data-tooltip='true'"
    ]
    for key, value in kwargs.items():
        s.append(f"data-tooltip-{key}='{escape(value)}'")
    attrs = " ".join(s)

    if not wrapping:
        return mark_safe(attrs)
    
    return mark_safe(f"<span {attrs}>{wrapping}</span>")


def get_kwargs(parser: Parser, tokens: list[str], kwarg_list: list[str] = None, absolute_tokens: list[str] = None, optional_tokens: dict[str, Any] = None) -> dict:
    had_kwargs = False
    kwargs = {}

    if not kwarg_list:
        kwarg_list = tuple()

    if not absolute_tokens:
        absolute_tokens = tuple()

    if not optional_tokens:
        optional_tokens = {}

    for i, token in enumerate(tokens):
        split = token.split("=")
        if len(split) == 1 and len(kwarg_list) > i:
            if split[0] in absolute_tokens:
                kwargs[split[0]] = True
                continue

            if had_kwargs:
                raise ValueError("Unexpected positional argument after keyword argument")
            
            kwargs[kwarg_list[i]] = parser.compile_filter(token)
        elif len(split) == 1:
            if split[0] in absolute_tokens:
                kwargs[split[0]] = True
                continue
            else:
                key = split[0]
                value = parser.compile_filter(key)
                kwargs[key] = value
        else:
            key = split[0]
            # if key not in kwargs_names:
            #     raise ValueError(f"Unexpected keyword argument {key}")
            if key in absolute_tokens:
                raise ValueError(f"Keyword argument {key} cannot be resolved; it will not be parsed as a variable.")
            
            kwargs[key] = parser.compile_filter(split[1])
            had_kwargs = True

    for kwarg in kwarg_list:
        if kwarg not in kwargs:
            raise TemplateSyntaxError(f"Missing required keyword argument {kwarg}")
        
    for key, value in optional_tokens.items():
        if key not in kwargs:
            kwargs[key] = value

    return kwargs

