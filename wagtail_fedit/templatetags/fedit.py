from django.template import library, Node, NodeList
from django.template.loader import render_to_string
from django.template.base import Parser, Token, TokenType
from django.template.base import FilterExpression
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.core import signing
from django.db import models

from wagtail.blocks import BoundBlock
from wagtail.models import Page
from wagtail import hooks
from urllib.parse import urlencode

import warnings

from ..toolbar import (
    FeditBlockEditButton,
    FeditFieldEditButton,
)
from ..utils import FEDIT_PREVIEW_VAR, get_field_content
from ..hooks import (
    CONSTRUCT_BLOCK_TOOLBAR,
    CONSTRUCT_FIELD_TOOLBAR,
)


register = library.Library()
url_value_signer = signing.TimestampSigner()


WARNING_FIELD_NAME_NOT_AVAILABLE = "Field name is not available in the context for field %(field)s."
WARNING_MODEL_INSTANCE_NOT_AVAILABLE = "Model instance is not available in the context for block %(block)s."


class BlockEditNode(Node):
    class UnpackError(Exception):
        pass

    def __init__(self,
            nodelist: NodeList = None,
            block: BoundBlock = None,
            block_id: str = None,
            field_name: str = None,
            model: models.Model = None,
            **extra,
        ):

        self.nl = nodelist
        self.block = block
        self.block_id = block_id
        self.field_name = field_name
        self.model = model
        self.extra = extra

    def render(self, context):
        block = self.block
        block_id = self.block_id
        field_name = self.field_name
        model = self.model
        extra = self.extra

        # Conversions for filterexpressions
        for k, e in extra.items():
            if isinstance(e, FilterExpression):
                extra[k] = e.resolve(context)

        if not field_name and "wagtail_fedit_field_name" in context:
            field_name = context["wagtail_fedit_field_name"]

        if isinstance(block, FilterExpression):
            block = block.resolve(context)
        if isinstance(block_id, FilterExpression):
            block_id = block_id.resolve(context)
        if isinstance(field_name, FilterExpression):
            field_name = field_name.resolve(context)
        if isinstance(model, FilterExpression):
            model = model.resolve(context)
        
        if not block_id and "block_id" not in context and not block:
            raise ValueError("Block ID is required")
        
        # `wagtail_fedit_instance` is provided after the form is saved.
        # This allows us to easily use the same instance across multiple views.
        # Model will only be provided initially when the block is rendered.
        model = model or context.get("wagtail_fedit_instance")
        context["wagtail_fedit_field_name"] = field_name
        context["wagtail_fedit_instance"] = model
        
        # Render the block or nodelist
        # This allows us to use the block as a block tag or as a simple tag.
        if block:
            try:
                context = context.flatten()
            except AttributeError:
                pass
            context.update(extra)
            rendered = block.render_as_block(context)
            self.has_block = True
        elif self.nl:
            rendered = self.nl.render(context)
            self.has_block = False
        else:
            raise ValueError("Block or nodelist is required")
        
        if not field_name:
            warnings.warn(WARNING_FIELD_NAME_NOT_AVAILABLE % {"field": field_name})
            return rendered
        
        if not model:
            warnings.warn(WARNING_MODEL_INSTANCE_NOT_AVAILABLE % {"block": block.label})
            return rendered
        
        # Get block id from block if bound or context.
        if not block_id and "block_id" in context:
            block_id = context["block_id"]
        elif not block_id and block and hasattr(block, "id"):
            block_id = block.id
        elif not block_id:
            raise ValueError("Block ID is required")

        # Check if the user has permission to edit the block.
        request = context.get("request")
        if request:
            if (
                not request.user.is_authenticated\
                or not request.user.has_perm("wagtailadmin.access_admin")\
                or not request.user.has_perm(f"{model._meta.app_label}.change_{model._meta.model_name}")    
                or not getattr(request, FEDIT_PREVIEW_VAR, False)
            ):
                
                return rendered

        # If the model is a page, we can redirect the user to the page editor.
        # This will act as a shortcut; jumping to the block inside of the admin.
        if isinstance(model, Page):
            admin_edit_url = _get_from_context_or_set(
                context, "page_base_edit_url",
                lambda: reverse(
                    "wagtailadmin_pages:edit",
                    args=[model.id],
                ),
            )
            admin_edit_url = f"{admin_edit_url}#block-{block_id}-section"
        else:
            admin_edit_url = None

        extra["has_block"] = self.has_block

        items = [
            FeditBlockEditButton(),
        ]

        for hook in hooks.get_hooks(CONSTRUCT_BLOCK_TOOLBAR):
            hook(request=request, items=items, model=model, block_id=block_id, field_name=field_name)

        items = [item.render(request) for item in items]
        items = list(filter(None, items))
        
        return render_to_string(
            "wagtail_fedit/content/editable_block.html",
            {
                "edit_url": self.get_edit_url(
                    block_id, field_name,
                    instance=model,
                    **extra,
                ),
                "admin_edit_url": admin_edit_url,
                "block_id": block_id,
                "model": model,
                "content": rendered,
                "field_name": field_name,
                "parent_context": context,
                "wagtail_fedit_field_name": field_name,
                "wagtail_fedit_instance": model,
                "toolbar_items": items,
            }
        )
    
    @staticmethod
    def pack(**kwargs) -> dict:

        packed = {}
        for k, v in kwargs.items():
            packed[k] = url_value_signer.sign(str(v))

        return packed
    
    @classmethod
    def unpack(cls, *expected: str, request = None) -> dict:
        if not request:
            raise ValueError("Request is required")
        
        unpacked = {}
        for key in expected:
            try:
                unpacked[key] = url_value_signer.unsign(
                    request.GET.get(key)
                )
            except signing.SignatureExpired:
                raise cls.UnpackError(f"Value for {key} has expired")
            except signing.BadSignature:
                raise cls.UnpackError(f"Invalid value for {key}")
            except TypeError:
                raise cls.UnpackError(f"Missing value for {key}")

        if not all([unpacked.get(key) for key in expected]):
            raise cls.UnpackError(f"Missing value for {key}")
        
        return unpacked

    @staticmethod
    def get_edit_url(block_id: str, field_name: str, instance: models.Model, **kwargs) -> str:
        base_url = reverse(
            "wagtail_fedit:edit_block",
            args=[block_id, field_name, instance._meta.app_label, instance._meta.model_name, instance.pk]
        )

        if not kwargs:
            return base_url

        packed = urlencode(
            BlockEditNode.pack(**kwargs),
        )
        return f"{base_url}?{packed}"



@register.tag(name="fedit_block")
def do_render_fedit_block(parser: Parser, token: Token):
    """
    This tag is used to render an editable block.

    This block will be wrapped and is able to be edited by the user on the frontend.

    We will require the block_id and field_name of the streamfield this block belongs to.

    You could omit needing to pass a block ID by passing in the StreamChild instance as opposed to the StructValue instance.
    
    Usage example 1:
        ```python
        {% fedit_block my_structvalue_instance block_id my_streamfield_attribute_name page_instance %}
        ```

    Optionally you can omit the block and pass in the block_id and field_name as keyword arguments.

    This will allow you to use the block as a block tag.

    Usage example 2:
        ```python
        {% fedit_block block_id=my_structvalue_instance field_name=my_streamfield_attribute_name model=page_instance %}
            <p>Some content before block</p>
            {% include_block my_block %}
            <p>Some content after block</p>
        {% unfedit_block %}
        ```
    """

    tokens = token.split_contents()
    _ = tokens.pop(0)
    kwargs_names = [
        "block", "block_id",
        "field_name", "model",
    ]

    kwargs = get_kwargs(parser, kwargs_names, tokens)
    
    if "block" not in kwargs:
        nodelist = parser.parse(("unfedit_block",))
        parser.delete_first_token()
    else:
        nodelist = None

    extra = {}
    for key, value in kwargs.items():
        if key not in kwargs_names:
            extra[key] = value

    return BlockEditNode(
        nodelist=nodelist,
        block=kwargs.get("block"),
        block_id=kwargs.get("block_id"),
        field_name=kwargs.get("field_name"),
        model=kwargs.get("model"),
        **extra,
    )


class FieldEditNode(Node):
    def __init__(self, model: models.Model, getters: list[str], inline: bool = False, **kwargs):
        self.model = model
        self.field = getters[len(getters)-1]
        self.getters = getters
        self.inline = inline
        self.kwargs = kwargs

    def render(self, context):
        getters = self.getters
        model = self.model
        inline = self.inline

        if isinstance(model, FilterExpression):
            model = model.resolve(context)

        if isinstance(inline, FilterExpression):
            inline = inline.resolve(context)

        obj = model
        for i in range(len(getters) - 1):
            getter = getters[i]
            try:
                obj = getattr(obj, getter)
            except AttributeError:
                raise AttributeError(f"Object {model.__class__.__name__} does not have attribute {getter}")

        request = context.get("request")
        content = get_field_content(
            request,
            obj,
            obj._meta.get_field(self.field),
            context,
        )

        if request:
            if (
                not request.user.is_authenticated\
                or not request.user.has_perm("wagtailadmin.access_admin")\
                or not request.user.has_perm(f"{obj._meta.app_label}.change_{obj._meta.model_name}")\
                or not getattr(request, FEDIT_PREVIEW_VAR, False)
            ):
                return content
            
        return render_editable_field(
            request=request, 
            content=content,
            field_name=self.field, 
            model=obj,
            context=context,
            inline=inline,
            **self.kwargs,
        )
    


@register.tag(name="fedit_field")
def do_render_fedit_field(parser: Parser, token: Token):
    """
    This tag is used to render an editable field.

    This field will be wrapped and is able to be edited by the user on the frontend.

    Usage example:
        ```python
        {% fedit_field mymodel.myfield inline=(default: False) key1=value1 key2=value2 %}
        ```

    Optionally your model can define a `render_fedit_{field_name}` method that will be used to render the field.
    This will allow you to use custom rendering logic if need be.
    """
    tokens = token.split_contents()
    _ = tokens.pop(0)
    model__field = tokens.pop(0)
    model_tokens = model__field.split(".")

    if len(model_tokens) < 2:
        raise ValueError("Model and field name are required")
    
    # mymodel.myfield
    # mymodel.related_field.myfield
    model = parser.compile_filter(model_tokens.pop(0))

    if tokens:
        kwargs_names = [
            "inline",
        ]

        kwargs = get_kwargs(parser, kwargs_names, tokens)
    else:
        kwargs = {}

    return FieldEditNode(
        model=model,
        getters=model_tokens,
        **kwargs,
    )


def render_editable_field(request, content, field_name, model, context, **kwargs):
    edit_url = reverse(
        "wagtail_fedit:edit_field",
        args=[field_name, model._meta.app_label, model._meta.model_name, model.pk]
    )

    if kwargs:
        packed = urlencode(
            BlockEditNode.pack(**kwargs),
        )
        edit_url = f"{edit_url}?{packed}"

    items = [
        FeditFieldEditButton(),
    ]

    for hook in hooks.get_hooks(CONSTRUCT_FIELD_TOOLBAR):
        hook(request=request, items=items, model=model, field_name=field_name)

    items = [item.render(request) for item in items]
    items = list(filter(None, items))

    kwargs["wagtail_fedit_field_name"] = field_name
    kwargs["wagtail_fedit_instance"] = model
    kwargs["inline"] = str(kwargs.get("inline", False)).lower() == "true"
    return render_to_string(
        "wagtail_fedit/content/editable_field.html",
        {
            "edit_url": edit_url,
            "field_name": field_name,
            "model": model,
            "content": content,
            "parent_context": context,
            "toolbar_items": items,
            **kwargs,
        },
        request=request,
    )

def get_kwargs(parser: Parser, kwarg_list: list[str], tokens: list[str]) -> dict:
    had_kwargs = False
    kwargs = {}

    # if len(tokens) > len(kwargs_names):
    #     raise ValueError("Invalid number of arguments provided, expected at most %d" % len(kwargs_names))

    for i, token in enumerate(tokens):
        split = token.split("=")
        if len(split) == 1:
            if had_kwargs:
                raise ValueError("Unexpected positional argument after keyword argument")
            
            kwargs[kwarg_list[i]] = parser.compile_filter(token)
        else:
            key = split[0]
            # if key not in kwargs_names:
            #     raise ValueError(f"Unexpected keyword argument {key}")
            
            kwargs[key] = parser.compile_filter(split[1])
            had_kwargs = True

    return kwargs




def _get_from_context_or_set(context, key, value, *args, **kwargs):
    if key in context:
        return context[key]
    
    if callable(value):
        value = value(*args, **kwargs)

    context[key] = value
    return value
    
