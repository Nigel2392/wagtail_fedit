// Title: Permissions
// Next: support.md
// Previous: settings.md
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
