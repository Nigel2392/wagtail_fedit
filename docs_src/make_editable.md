{{ Set "Title" "Making your models editable" }}

## Getting Editing!
1. If you want to get into the frontend-editing interface for a model it must inherit from `PreviewableMixin`.

   **This is a requirement.**

   It is however not always required for your model to inherit from `PreviewableMixin`.

   **Any model can be edited**; you just can't access the specific frontend editing interface URL for that model if it does not inherit from `PreviewableMixin`.

   I.E: If a random model which does not inherit from `PreviewableMixin` appears on an editable page; **you will be able to edit it.**
2. Define a template for your model.

   Example:

   ```html
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

   ```html
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