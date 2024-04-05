from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.BatteryListAPIView.as_view(), name="battery_list"),
    path("type/", views.BatteryTypeAPIView.as_view(), name="battery_type"),
    # path("<str:ds>/", views.BatteryListByDatasetView.as_view(), name="battery_list_by_dataset"),
    path("battery/<str:pk>/", views.BatteryDetailAPIView.as_view(), name="battery_detail"),
]