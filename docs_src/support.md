// Title: Supported Features
// Previous: permissions.md

# Supported Features

A list of features that are supported out of the box.

## Permissions

Permissions are included out of the box.
We will automatically check if the user has the correct permissions to edit the object.
If they do not, they cannot access the editable page.

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

