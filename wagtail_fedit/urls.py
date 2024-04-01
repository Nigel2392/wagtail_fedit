from django.urls import path, include
from . import views

app_name = "wagtail_fedit"

urlpatterns = [
    path("editable/<str:object_id>/<str:app_label>/<str:model_name>/", views.FEditableView.as_view(), name="editable"),
    path("publish/<str:object_id>/<str:app_label>/<str:model_name>/", views.FeditablePublishView.as_view(), name="publish"),
    path("field/<str:field_name>/<str:app_label>/<str:model_name>/<str:model_id>/", views.EditFieldView.as_view(), name="edit_field"),
    path("edit_block/<str:block_id>/<str:field_name>/<str:app_label>/<str:model_name>/<str:model_id>/", views.EditBlockView.as_view(), name="edit_block"),
]