# Generated by Django 5.0.4 on 2024-04-05 12:32

import django.db.models.deletion
import wagtail.blocks
import wagtail.fields
import wagtail_fedit.test.core.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_basicmodel_content_editabledraftmodel_content_and_more'),
        ('wagtailcore', '0091_remove_revision_submitted_for_moderation'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EditableLockModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('live', models.BooleanField(default=True, editable=False, verbose_name='live')),
                ('has_unpublished_changes', models.BooleanField(default=False, editable=False, verbose_name='has unpublished changes')),
                ('first_published_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='first published at')),
                ('last_published_at', models.DateTimeField(editable=False, null=True, verbose_name='last published at')),
                ('go_live_at', models.DateTimeField(blank=True, null=True, verbose_name='go live date/time')),
                ('expire_at', models.DateTimeField(blank=True, null=True, verbose_name='expiry date/time')),
                ('expired', models.BooleanField(default=False, editable=False, verbose_name='expired')),
                ('locked', models.BooleanField(default=False, editable=False, verbose_name='locked')),
                ('locked_at', models.DateTimeField(editable=False, null=True, verbose_name='locked at')),
                ('title', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('content', wagtail.fields.StreamField([('heading_component', wagtail.blocks.StructBlock([('heading', wagtail.blocks.CharBlock(max_length=25)), ('subheading', wagtail.blocks.CharBlock(max_length=40))])), ('flat_menu_component', wagtail.blocks.StructBlock([('title', wagtail.blocks.CharBlock(max_length=25)), ('subtitle', wagtail.blocks.RichTextBlock()), ('items', wagtail.blocks.ListBlock(wagtail.blocks.StructBlock([('link', wagtail.blocks.StructBlock([('text', wagtail.blocks.CharBlock(max_length=25))]))])))]))])),
                ('latest_revision', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.revision', verbose_name='latest revision')),
                ('live_revision', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailcore.revision', verbose_name='live revision')),
                ('locked_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='locked_%(class)ss', to=settings.AUTH_USER_MODEL, verbose_name='locked by')),
            ],
            options={
                'abstract': False,
            },
            bases=(wagtail_fedit.test.core.models.BaseEditableMixin, models.Model),
        ),
    ]