wagtail_fedit
=============

![Wagtail FEdit Example](https://github.com/Nigel2392/wagtail_fedit/blob/main/.github/images/wagtail_fedit_example.png?raw=true)

Wagtail FEdit is a library to allow your Wagtail pages and content-blocks to be edited on the frontend.

# Table of Contents

- [Getting Started](#getting-started)
- [Getting Editing!](#getting-editing)
- [Permissions](#permissions)
- [Revisions](#revisions)
- [Workflows](#workflows)
- [Logs](#logs)
- [Caveats](#caveats)
- [Adapters](#adapters)
  - [Adapters Python](#adapters-python)
  - [Adapters Javascript](#adapters-javascript)
- [Hooks](#hooks)
  - [Construct Adapter Toolbar](#wagtail_feditconstruct_adapter_toolbar)
  - [Register Type Renderer](#wagtail_feditregister_type_renderer)
  - [Register Field Renderer](#wagtail_feditregister_field_renderer)
  - [Register Field Widgets](#wagtail_feditregister_field_widgets)
  - [Exclude Related Forms](#wagtail_feditexclude_related_forms)
  - [Action Menu Item Is Shown](#wagtail_feditaction_menu_item_is_shown)
  - [Register CSS](#wagtail_feditregister_css)
  - [Register JS](#wagtail_feditregister_js)
  - [Field Editor Size](#wagtail_feditfield_editor_size)
- [Settings](#settings)
  - [Sign Shared Context](#wagtail_fedit_sign_shared_context)
  - [Share With Sessions](#wagtail_fedit_share_with_sessions)
  - [Use Adapter Session ID](#wagtail_fedit_use_adapter_session_id)
- [How your content is rendered](#how-your-content-is-rendered)
  - [Rendered output HTML](#rendered-editable-output-html)
- [Implemented](#implemented)

Getting Started
---------------

1. Add 'wagtail_fedit' to your INSTALLED_APPS setting like this:

   ```
   INSTALLED_APPS = [
   ...,
   'wagtail_fedit',
   ]
   ```
2. Run `py ./manage.py collectstatic`.
3. Run `py ./manage.py adapter_help` to see all your options and their requirements.

## Getting Editing!

1. If you want to get into the frontend-editing interface for a model it must inherit from `PreviewableMixin`.

   **This is a requirement.**

   It is however not always required for your model to inherit from `PreviewableMixin`.

   **Any model can be edited**; you just can't access the specific frontend editing interface URL for that model if it does not inherit from `PreviewableMixin`.

   I.E: If a random model which does not inherit from `PreviewableMixin` appears on an editable page; **you will be able to edit it.**

2. Define a template for your model.

   Example:

   ```django-html
   {% load fedit static wagtailuserbar %} {# Load the required template tag libraries #}
   <!DOCTYPE html>
   <html lang="en">
   <head>
       <meta charset="UTF-8">
       <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <title>Document</title>
       {# Load all registered CSS required for the adapters. Only included inside edit view! #}
       {% fedit_scripts "css" %}
   </head>
   <body>
       {# Adress the model.field or model.my.related.field you wish to edit. #}
       {# For help on arguments for the adapters please run the adapter_help command. #}
       {# Example: `python3 ./manage.py adapter_help` #}
       <h1>{% fedit field self.title inline %}</h1>

       <main class="my-streamfield-content">
           {% fedit field self.content %}
       </main>

       {% wagtailuserbar %}

       {# Load all registered Javascript required for the adapters. Only included inside edit view! #}
       {% fedit_scripts "js" %}
   </body>
   </html>


   ```
3. If your needs some special form of rendering; we allow your model to define a custom render method.
   The format of the method name should be `render_fedit_{fieldname}`.
   Say we want all sub-blocks of our streamfield to automatically be made editable. This wouldn't be possible in the above configuration.
   To fix this; we should first create a custom template to render our content.

   Example:

   ```django-html
   {# myapp/render_my_field.html #}
   {% load fedit %}
   {% for block in self.content %}
       {# Sub-Blocks wrapped by {# fedit block #} do not require the field_name or model argument. #}
       {# This can (and probably should be) replaced with the `from_context` argument. #}
       {# The variables are then taken from the parent {% fedit %} tag. The model and field name are shared through context. #}
       {# This keeps everything extensible; but in this case it does not matter since what we are doing is instance- specific. #}
       {% fedit block self.content block=block block_id=block.id %}
   {% endfor %}

   ```

   ```python
   from django.template.loader import render_to_string
   ...

   class MyPage(...): # Can be any type of model.
       content = StreamField(...)

       def render_fedit_content(self, request, context):
           return render_to_string("myapp/render_my_field.html", self.get_context(request) | context)
   ```

   Your content will then automatically be rendered with that method when need be by using
   `{% fedit field self.content %} `
4. **But wait?! I go to my template and I do not see a way to edit!** That is true! We try to protect any styling on your actual page; we do not want to interfere.Instead; we serve the editing interface on a different URL, accessible by clicking `Frontend Editing` in the Wagtail userbar. Keep an eye on that userbar! It is also used for publishing if your model inherits from `DraftStateMixin`.

**Note:** If the parent block is wrapped with `{% fedit block %}` or `{% fedit field %}` passing in the instance variable and field name should be omitted and replaced with `from_context`.
Example: `{% fedit block from_context block=item block_id=item.id %}`
The parent- blocktag will share these variables through context.
This makes it possibly to easily use editable sub-blocks across multiple different model types.
If your model **ISN'T** capable of editing; or these variables aren't shared - your block will be rendered as normal.

## Permissions

**Note: This is not required for pages.**

**The `Page` model already provides this interface.**

We have the following basic permission requirements:

* You must have `wagtailadmin.access_admin` to edit a block/field.
* You must have the appropriate `app_label.change_*` permission for the model.

This however only applies to editing.

We use separate permissions for publishing and submitting workflows, etc.

Models which you want to allow the publish view for should also implement a `PermissionTester`- like object.

Example of how you should implement the `Tester` object and all required permissions. (More details in `models.py`)

```python

class MyModel(...):
    def permissions_for_user(self, user):
        return MyModelPermissionTester(self, user)

class MyModelPermissionTester(...):
    def can_unpublish(self):
        """ Can the user unpublish this object? (Required for un-publishing"""
  
    def can_publish(self):
        """ Can the user publish this object? (Required for publishing)"""  
  
    def can_submit_for_moderation(self):
        """ Can the user submit this object for moderation? (Optional) """

```

## Revisions

Revision support is included out of the box.
If your model inherits from a `RevisionMixin`, we will automatically create drafts for you.
These will not be published (If the model inherits from `DraftStateMixin`) until you choose to do so.

## Workflows

We include a `WorkFlow` to submit this object for moderation.

More workflow support will be included in the future.

## Logs

Logs are also included out of the box.
We will automatically update your model's history; including possible revisions.
This will allow you to backtrack each change made on the frontend.
This however does mean that a possibly large amount of data will be stored in your database.

## Caveats

Wagtail does not always make it's `id` attribute available.

This is only available to instances of `StreamChild` and `ListChild`.

Consider the following regular wagtail list loop where `items` is a `ListBlock`.

```django-html
{% for item in self.items %}
    {% include_block item %} {# No access to ID! Cannot edit! #}
{% endfor %}
```

To make this an editable block instead; we would slightly change the loop to make the block's `id` available.

This is done by accessing the `bound_blocks` of that ListBlock *(`StreamBlock` does this automatically for the toplevel block!)*

Our new loop would then be:

```django-html
{% for item in self.items.bound_blocks %}
    {# Field name and model are the same arguments as in the first example! #}
    {% fedit block my_model_instance_var.content_field block=item block_id=item.id %}
{% endfor %}
```

## Adapters

Creating a custom adapter is relatively simple.
We highly recommend you to inherit from `BaseFieldFuncAdapter` or `BaseBlockFuncAdapter`.
These adapters are basically pre-setup to callback to a javascript function on successful form submission.
This will save you the most amount of work.

We will create an adapter to change the color of a text field.

Our adapter will be called `colorizer`.

1. Our model is defined as follows:

```python
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from django.db import models

class MyPage(Page):
    COLOR_CHOICES = [
        ("#000000", "Black"),
        ("#FFFFFF", "White"),
        ("#FF0000", "Red"),
        ("#00FF00", "Green"),
        ("#0000FF", "Blue"),
    ]

    color = models.CharField(max_length=7, default="#000000", choices=COLOR_CHOICES)

    content_panels = Page.content_panels + [
        FieldPanel("color"),
    ]
```

2. We have the following HTML template:

```django-html
...

{% load fedit %}
{% fedit colorizer page.color target=".my-colorized-div" %}
<div class="my-colorized-div" style="color: {{ page.color }}">
    <h1>Colorized Text!</h1>
</div>

...
```

### Adapters Python

We will get started creating the adapter definition.
Adapters can be defined anywhere; we recommend a separate `adapters.py` file.

Adapter instances also have access to the following variables:

* `self.object` - The model instance.
* `self.field_name` - The field name.
* `self.meta_field` - The models.Field instance.
* `self.field_value` - The field value (Retrieved with `self.meta_field.value_from_object(self.object)`)
* `self.request` - The django HTTP request object.
* `self.kwargs` - Any shared context / keyword arguments for this adapter.

```python
# myapp/adapters.py

from wagtail_fedit.adapters import (
    BaseFieldFuncAdapter,
    VARIABLES,
)

class ColorizerAdapter(BaseFieldFuncAdapter):
    # Required keyword arguments for the template tag are defined by the superclass.
    # required_kwargs = [
    #   "target",
    #   "name", # the function name, override in __init__ method.
    # ]

    # Optional kwargs are used to inform inside of the adapter_help command.
    # They are only for developer convenience.
    # optional_kwargs = []

    # How the adapter will be adressed inside of the template tag.
    identifier = "colorizer"

    # A simple description of what this adapter does.
    usage_description = "Change the color of the text for the given target element."

    # Optional explanation of keyword arguments
    help_text_dict = {
        "target": "The target element to apply the color to.",
    }

    def __init__(self, object, field_name: str, request: HttpRequest, **kwargs):
        kwargs["name"] = "myColorizerJavascriptFunction"
        super().__init__(object, field_name, request, **kwargs)

    def render_content(self, parent_context=None):
        # This is not required; we will replace a CSS variable; thus we are not returning any actual content.
        return ""
  
    def get_response_data(self, parent_context=None):
        """
        Return the data to be sent to the frontend adapter.
        """
        data = super().get_response_data(parent_context)
        return data | {
            "color": self.field_value,
        }

    def get_form_attrs(self) -> dict:
        """
        Return form attributes for the form inside of the edit modal.
        This can be used to control editor size.
        """
        attrs = super().get_form_attrs()
        attrs[VARIABLES.FORM_SIZE_VAR] = "full" # Fullscreen, there is also `large`.
        return attrs
```

We must then register the adapter to make sure it is available for templates.

This should be done in a `wagtail_hooks.py` file.

```python
# myapp/wagtail_hooks.py

from wagtail_fedit.adapters import adapter_registry
from myapp.adapters import ColorizerAdapter

adapter_registry.register(ColorizerAdapter)
```

### Adapters Javascript

We now need to create the javascript function to actually apply the color to the styles of the element.
This function will be called `myColorizerJavascriptFunction`, as defined in the adapter's `__init__` method.

```javascript
// myapp/static/myapp/js/custom.js
function myColorizerJavascriptFunction(element, response) {
    element.style.color = response.color;
}
```

We must then register this javascript file to be included in the frontend editing interface.

This should be done in a `wagtail_hooks.py` file.

```python
# myapp/wagtail_hooks.py

from django.utils.html import format_html
from django.templatetags.static import static
from wagtail_fedit.hooks import REGISTER_JS
from wagtail import hooks

@hooks.register(REGISTER_JS)
def register_js(request):
    return [
        format_html(
            '<script src="{0}"></script>',
            static('myapp/js/custom.js')
        ),
    ]
```

## Hooks

### wagtail_fedit.construct_adapter_toolbar

Construct the toolbar for the given adapter.
This is used to display the edit icon for the given adapter.

How it is called:

```python
items = [
    FeditAdapterEditButton(),
]
for hook in hooks.get_hooks(CONSTRUCT_ADAPTER_TOOLBAR):
    hook(items=items, adapter=adapter)
```

### wagtail_fedit.register_type_renderer

Register a custom renderer for a type.

Example of how this type of renderer can be used:

```python
@hooks.register(REGISTER_TYPE_RENDERER)
def register_renderers(renderer_map):

    # This is a custom renderer for the Page model.
    # It will render the Page model as a simple h2 tag.
    renderer_map[Page] = lambda request, context, instance, value: format_html(
        '<h2>{0}</h2>',
        value.title
    )
```

### wagtail_fedit.register_css

Register a custom CSS file to be included when the utils.FEDIT_PREVIEW_VAR is set to True.

Example of how this hook is used in wagtail_hooks.py:

```python
@hooks.register(REGISTER_CSS)
def register_css(request):
    return [
        format_html(
            '<link rel="stylesheet" href="{0}">',
            static('css/custom.css')
        ),
    ]
```

### wagtail_fedit.field_editor_size

Control the size of the editor for the given model-field type.

Example of how this hook is called:

```python
for hook in hooks.get_hooks(FEDIT_FIELD_EDITOR_SIZE):
    size = hook(model_instance, model_field)
    if size:
        return size
```

### wagtail_fedit.register_js

Register a custom JS file to be included when the utils.FEDIT_PREVIEW_VAR is set to True.

This can be used to register custom adapter JS.

Example of how this hook is used in wagtail_hooks.py:

```python
@hooks.register(REGISTER_JS)
def register_js(request):
    return [
        format_html(
            '<script src="{0}"></script>',
            static('js/custom.js')
        ),
    ]
```

### wagtail_fedit.register_field_renderer

Register a custom renderer for a field.

Example of how this type of renderer is used in wagtail_hooks/renderers.py:

```python
@hooks.register(REGISTER_FIELD_RENDERER)
def register_renderers(renderer_map):

    # This is a custom renderer for RichText fields.
    # It will render the RichText field as a RichText block.
    renderer_map[RichTextField] =\
        lambda request, context, instance, value: richtext(value)
```

### wagtail_fedit.register_field_widgets

Register a custom widget for a field.

Example of how this hook is used in wagtail_hooks.py:

```python
@hooks.register(REGISTER_FIELD_WIDGETS)
def register_field_widgets(widgets):
    widgets[RichTextField] = AdminRichTextField
    return widgets
```

### wagtail_fedit.exclude_related_forms

Exclude the given model type from the related forms.
This is used internally to exclude the Page, Image, and Document models from the related forms.
This way; the user will have the actual widget for the field instead of the related form.

Example of how this hook is called and how it is used internally:

```python
def use_related_form(field: models.Field) -> bool:
    for hook in hooks.get_hooks(EXCLUDE_FROM_RELATED_FORMS):
        if hook(field):
            return False
    return True

  
@hooks.register(EXCLUDE_FROM_RELATED_FORMS)
def exclude_related_forms(field):
    if field.related_model in [Page, Image, Document]:
        return True
    return False
```

### wagtail_fedit.action_menu_item_is_shown

Decide if the action menu item should be shown for the given instance.

Return None if you cannot decide, False if you want to hide the item, and True if you want to show the item.

Example of how this hook is called:

```python
for hook in hooks.get_hooks(ACTION_MENU_ITEM_IS_SHOWN):
    result = hook(context, instance)
    if result is not None:
        return result # <- bool
```

## Settings

### `WAGTAIL_FEDIT_SIGN_SHARED_CONTEXT`

Default: `True`

Sign the shared context with a secret key.
This is useful to prevent tampering with the shared context.
It will also be compressed with zlib if available.
It might not be in your site's security model to need this.

### `WAGTAIL_FEDIT_SHARE_WITH_SESSIONS`

Default: `False`

Share the context through the session data.
This is useful if you are running into limits with the URL length.
This will store the context in the session and pass the session
key to the iFrame instead of the context.

### `WAGTAIL_FEDIT_USE_ADAPTER_SESSION_ID`

Default: `True`

Use the get_element_id method of the adapter to generate a session ID.
*This could __maybe__ interfere with other editable- block's session data, but is highly unlikely!*
This is useful to not clutter session data too much.
If `False`, the session ID will be generated each time the page is loaded.

### `WAGTAIL_FEDIT_TRACK_LOCALES`

Default: `False`

Track the locales of the users across the views.

**This sets the initial request.LANGUAGE_CODE (if available) in the shared context.**

If this is false, there is no guarantee that the language of a saved field/model
will be the same as it initially was, generally it will be - however this might mess up with Wagtail's `Page.locale` and
the page not being available in the context afterwards.

## How your content is rendered

(**Maintainer's note:** In my experience this doesn't mess the CSS up too much, or even at all for most content - **if** you don't get hyperspecific with your CSS selectors and structure your templates well.)

Your block and field are wrapped in a `div`, any CSS for your templates should keep this in mind.

### Rendered editable output HTML

```html
{% load fedit %}<div id="{{ adapter.get_element_id }}" class="wagtail-fedit-adapter-wrapper{% if shared_context.inline or adapter.inline %} wagtail-fedit-inline{%endif%} wagtail-fedit-{{ identifier }}" data-fedit-constructor="{{ js_constructor }}" {% if shared %} data-shared-context="{{ shared }}"{%endif%} data-edit-url="{{ edit_url }}">
    <div class="wagtail-fedit-buttons">
        {% for button in buttons %}
            {{ button }}
        {% endfor %}
    </div>{% render_adapter adapter %}
</div>
```

## Implemented

* Revision Support
* Locked Support
* Draft Support
* Preview Support
* Workflow Support
* Permissions
* Audit Logs
* Full block capabilities on Frontend Editing
