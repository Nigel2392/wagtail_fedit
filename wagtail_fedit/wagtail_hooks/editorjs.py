
try:
    from wagtail_editorjs import blocks
    from wagtail_editorjs import django_editor
    from wagtail import hooks
    
    import wagtail_fedit.hooks

    @hooks.register(wagtail_fedit.hooks.REGISTER_BLOCK_HOOK_NAME)
    def register_fedit_blocks(block_map):
        block_map[blocks.EditorJSBlock] = django_editor.DjangoEditorJSFormField

except ImportError:
    pass

