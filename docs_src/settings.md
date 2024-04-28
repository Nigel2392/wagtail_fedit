{{ Set "Title" "Django Settings" }}
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

### `WAGTAIL_FEDIT_TIPPY_ENABLED`

Default: `True`

Enable Tippy.js tooltips for toolbar buttons.
