from django.urls import path
from . import views

app_name = "wagtail_fedit"

urlpatterns = []

adapter_based_views = (
    ("edit", views.EditAdapterView),
    ("refetch", views.AdapterRefetchView),
)
 
for name, view in adapter_based_views:
    view.url_name = f"wagtail_fedit:{name}"
    view.url_pattern = view.prefix_url_path(name)
    urlpatterns.append(
        path(view.url_pattern, view.as_view(), name=name)
    )
    view.url_pattern = f"{name}/<str:adapter_id>/<str:app_label>/<str:model_name>/<str:model_id>/"
    urlpatterns.append(
        path(view.url_pattern, view.as_view(), name=name)
    )

# Model based views
model_based_views = (
    ("editable", views.FEditableView),
    ("publish", views.PublishView),
    ("submit", views.SubmitView),
    ("unpublish", views.UnpublishView),
    ("cancel", views.CancelView),
)

for name, view in model_based_views:
    view.url_name = f"wagtail_fedit:{name}"
    view.url_pattern = f"{name}/<str:object_id>/<str:app_label>/<str:model_name>/"
    urlpatterns.append(
        path(view.url_pattern, view.as_view(), name=name)
    )
