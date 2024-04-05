from django.urls import path, include
from . import views

app_name = "wagtail_fedit"

urlpatterns = [
    # Preview
    path("editable/<str:object_id>/<str:app_label>/<str:model_name>/", views.FEditableView.as_view(), name="editable"),

    # Submit Views
    path("publish/<str:object_id>/<str:app_label>/<str:model_name>/", views.PublishView.as_view(), name="publish"),
    path("submit/<str:object_id>/<str:app_label>/<str:model_name>/", views.SubmitView.as_view(), name="submit"),
    path("unpublish/<str:object_id>/<str:app_label>/<str:model_name>/", views.UnpublishView.as_view(), name="unpublish"),
    # path("cancel/<str:object_id>/<str:app_label>/<str:model_name>/", views.CancelView.as_view(), name="cancel"),

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