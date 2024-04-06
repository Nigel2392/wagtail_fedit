from django.urls import path, include
from . import views

app_name = "wagtail_fedit"

urlpatterns = [
    # Frontend Editing
    path(
        "field/<str:field_name>/<str:app_label>/<str:model_name>/<str:model_id>/", 
        views.EditFieldView.as_view(), name="edit_field"
    ),
    path(
        "block/<str:block_id>/<str:field_name>/<str:app_label>/<str:model_name>/<str:model_id>/", 
        views.EditBlockView.as_view(), name="edit_block"
    ),
]

model_based_views = (
    ("editable", views.FEditableView),
    ("publish", views.PublishView),
    ("submit", views.SubmitView),
    ("unpublish", views.UnpublishView),
)

for name, view in model_based_views:
    view.url_name = f"wagtail_fedit:{name}"
    view.url_pattern = f"{name}/<str:object_id>/<str:app_label>/<str:model_name>/"
    urlpatterns.append(
        path(view.url_pattern, view.as_view(), name=name)
    )
