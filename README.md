wagtail_fedit
=============

Wagtail FEdit is a library to allow your Wagtail pages and content-blocks to be edited on the frontend.

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
   <!DOCTYPE html>
   <html lang="en">
   <head>
       <meta charset="UTF-8">
       <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <title>Document</title>
       <link rel="stylesheet" href="{% static 'wagtail_fedit/css/frontend.css' %}">
   </head>
   <body>
       {% load fedit %} {# Load the template tag library #}

       {# Pass in the field_name and the model instance on which that field resides. #}
       <h1>{% fedit_field "title" self %}</h1>

       {# Pass in the field_name and the model instance on which that field resides. #}
       <main class="my-streamfield-content">
           {% fedit_field "content" self %}
       </main>

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
       {% fedit_block block=block block_id=block.id field_name="content" model=self %}
   {% endfor %}

   ```

   ```python
   from django.template.loader import render_to_string
   ...

   class MyPage(...): # Can be any type of model.
       content = StreamField(...)

       def render_fedit_content(self, request):
           return render_to_string("myapp/render_my_field.html", self.get_context(request))
   ```

   Your content will then automatically be rendered with that method when need be by using `{% fedit_field "content" self %}`

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
    {% fedit_block block=item block_id=item.id field_name="content" model=self %}
{% endfor %}
```

## Settings

## Models/Methods
