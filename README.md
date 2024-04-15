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
- [Hooks](#hooks)
  - [Construct Adapter Toolbar](#wagtail_feditconstruct_adapter_toolbar)
  - [Register Type Renderer](#wagtail_feditregister_type_renderer)
  - [Register Field Renderer](#wagtail_feditregister_field_renderer)
  - [Exclude Related Forms](#wagtail_feditexclude_related_forms)
  - [Action Menu Item Is Shown](#wagtail_feditaction_menu_item_is_shown)
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

## Getting Editing!

1. Make sure the models you wish to edit inherit from PreviewableMixin.

   **This is a requirement.**
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
       <link rel="stylesheet" href="{% static 'wagtail_fedit/css/frontend.css' %}">
   </head>
   <body>
       {# Adress the model.field or model.my.related.field you wish to edit. #}
       {# Editable fields get a special `inline` argument. #}
       {# if True the button is not placed with an absolute CSS position. #}
       <h1>{% fedit field self.title inline=True or False %}</h1>

       <main class="my-streamfield-content">
           {% fedit field self.content %}
       </main>

       {% wagtailuserbar %}

       <script src="{% static 'wagtail_fedit/js/frontend.js' %}"></script>
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

## How your content is rendered

(**Maintainer's note:** In my experience this doesn't mess the CSS up too much, or even at all for most content - **if** you don't get hyperspecific with your CSS selectors and structure your templates well.)

Your block and field are wrapped in a `div`, any CSS for your templates should keep this in mind.

### Rendered editable output HTML

```html
<div class="wagtail-fedit-adapter-wrapper{%if shared_context.inline%} wagtail-fedit-inline{%endif%} wagtail-fedit-{{ identifier }}"{% if shared %} data-shared-context="{{ shared }}"{%endif%} data-edit-url="{{ edit_url }}">
    <div class="wagtail-fedit-buttons">
        {% for button in buttons %}
            {{ button }} {# Edit button; more buttons MIGHT possibly be added in the future. #}
        {% endfor %}
    </div>{{ content|safe }}
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
