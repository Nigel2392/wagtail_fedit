{{ Set "Title" "Installation Instructions" }}
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