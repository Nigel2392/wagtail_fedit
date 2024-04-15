from typing import Type
from django.template import library, Node, TemplateSyntaxError
from django.template.loader import render_to_string
from django.template.base import Parser, Token
from django.template.base import FilterExpression
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
)
from ..hooks import (
    CONSTRUCT_ADAPTER_TOOLBAR,
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


def wrap_adapter(request: HttpRequest, adapter: BaseAdapter, context: dict) -> str:
    if not context:
        context = {}

    context["wagtail_fedit_field"] = adapter.field_name
    context["wagtail_fedit_instance"] = adapter.object
    
    context["request"] = request

    content = adapter.render_content(context)
    shared = adapter.encode_shared_context()

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

    return render_to_string(
        "wagtail_fedit/content/editable_adapter.html",
        {
            "request": request,
            "identifier": adapter.identifier,
            "content": content,
            "adapter": adapter,
            "buttons": items,
            "shared": shared,
            "shared_context": adapter.kwargs,
            "edit_url": reverse(
                "wagtail_fedit:edit",
                kwargs=reverse_kwargs,
            ),
        },
        request=request,
    )


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

