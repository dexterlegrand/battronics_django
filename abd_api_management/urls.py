from django.urls import path, include
from . import views

urlpatterns = [
    path("resources/dataset/", views.DatasetView.as_view(), name="dataset"),
]