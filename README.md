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
       {# Pass in the field_name and the model instance on which that field resides. #}
       <h1>{% fedit_field "title" self %}</h1>

       {# Pass in the field_name and the model instance on which that field resides. #}
       <main class="my-streamfield-content">
           {% fedit_field "content" self %}
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

   Your content will then automatically be rendered with that method when need be by using `{% fedit_field "content" self %} `

4. **But wait?! I go to my template and I do not see a way to edit!**  
   That is true! We try to protect any styling on your actual page; we do not want to interfere.  
   Instead; we serve the editing interface on a different URL, accessible by clicking `Frontend Editing` in the Wagtail userbar.  
   Keep an eye on that userbar! It is also used for publishing if your model inherits from `DraftStateMixin`.
   
## Revisions

Revision support is included out of the box.
If your model inherits from a `RevisionMixin`, we will automatically create drafts for you.
These will not be published (If the model inherits from `DraftStateMixin`) until you choose to do so.

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
    {% fedit_block block=item block_id=item.id field_name="content" model=self %}
{% endfor %}
```

## Settings

## Models/Methods
