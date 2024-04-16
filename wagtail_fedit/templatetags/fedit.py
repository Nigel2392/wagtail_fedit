from typing import Type
from django.template import (
    library, Node, TemplateSyntaxError,
)
from django.template.loader import render_to_string
from django.template.context import (
    Context,
)
from django.template.base import (
    Parser, Token,
    FilterExpression,
)
from django.http import HttpRequest
from django.urls import reverse
from django.core import signing

from wagtail import hooks

import warnings

from ..toolbar import (
    FeditAdapterEditButton,
)
from ..adapters import (
    adapter_registry,
    RegistryLookUpError,
    BaseAdapter,
    AdapterError,
)
from ..utils import (
    _can_edit,
    FEDIT_PREVIEW_VAR,
)
from ..hooks import (
    CONSTRUCT_ADAPTER_TOOLBAR,
    REGISTER_CSS,
    REGISTER_JS,
)


register = library.Library()


WARNING_FIELD_NAME_NOT_AVAILABLE = "Field name is not available in the context for %(object)s."
WARNING_MODEL_INSTANCE_NOT_AVAILABLE = "Model instance is not available in the context for %(object)s."



class AdapterNode(Node):
    signer = signing.TimestampSigner()

    def __init__(self, adapter: Type[BaseAdapter], model: FilterExpression, getters: list[str], **kwargs):
        self.adapter = adapter
        self.model = model
        self.getters = getters
        self.kwargs = kwargs

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
            and not model:

            field_name = context["wagtail_fedit_field"]
            obj = context["wagtail_fedit_instance"]

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
                    return self.adapter.render_from_kwargs(
                        context, **kwargs,
                    )
                except AdapterError as e:
                    raise TemplateSyntaxError(str(e))

            field_name = getters[len(getters)-1]
            obj = model
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
            return adapter.render_content(context)

        return wrap_adapter(request, adapter, context)


@register.tag(name="fedit")
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

        if len(model_tokens) < 2:
            if model_tokens[0] != "from_context":
                raise TemplateSyntaxError(
                    "Model and field name are required: 'mymodel.myfield' or 'from_context'",
                )

        if len(model_tokens) > 1:
            # mymodel.myfield
            # mymodel.related_field.myfield
            model = parser.compile_filter(model_tokens.pop(0))

    kwargs = get_kwargs(parser, tokens, adapter.required_kwargs)

    return AdapterNode(
        adapter=adapter,
        model=model,
        getters=model_tokens,
        **kwargs,
    )


def wrap_adapter(request: HttpRequest, adapter: BaseAdapter, context: dict, run_context_processors: bool = False) -> str:
    if not context:
        context = {}

    items = [
        FeditAdapterEditButton(),
    ]

    for hook in hooks.get_hooks(CONSTRUCT_ADAPTER_TOOLBAR):
        hook(items=items, adapter=adapter)

    items = [item.render(request) for item in items]
    items = list(filter(None, items))

    reverse_kwargs = {
        "adapter_id": adapter.identifier,
        "field_name": adapter.field_name,
        "app_label": adapter.object._meta.app_label,
        "model_name": adapter.object._meta.model_name,
        "model_id": adapter.object.pk,
    }

    shared = adapter.encode_shared_context()
    js_constructor = adapter.get_js_constructor()
    
    return render_to_string(
        "wagtail_fedit/content/editable_adapter.html",
        {
            "identifier": adapter.identifier,
            "adapter": adapter,
            "buttons": items,
            "shared": shared,
            "js_constructor": js_constructor,
            "shared_context": adapter.kwargs,
            "parent_context": context,
            "edit_url": reverse(
                "wagtail_fedit:edit",
                kwargs=reverse_kwargs,
            ),
        },
        request=request if run_context_processors else None,
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

    return adapter.render_content(context)


@register.inclusion_tag("wagtail_fedit/_hook_output.html", name="fedit_scripts", takes_context=True)
def static_hook_output(context, css_or_js) -> dict:
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


def get_kwargs(parser: Parser, tokens: list[str], kwarg_list: list[str] = None) -> dict:
    had_kwargs = False
    kwargs = {}

    if not kwarg_list:
        kwarg_list = []

    for i, token in enumerate(tokens):
        split = token.split("=")
        if len(split) == 1 and len(kwarg_list) > i:
            if had_kwargs:
                raise ValueError("Unexpected positional argument after keyword argument")
            
            kwargs[kwarg_list[i]] = parser.compile_filter(token)
        else:
            key = split[0]
            # if key not in kwargs_names:
            #     raise ValueError(f"Unexpected keyword argument {key}")
            
            kwargs[key] = parser.compile_filter(split[1])
            had_kwargs = True

    for kwarg in kwarg_list:
        if kwarg not in kwargs:
            raise TemplateSyntaxError(f"Missing required keyword argument {kwarg}")

    return kwargs

