from django.urls import path

from . import views

app_name = 'abd_predictions'

urlpatterns = [
    path('<int:battery_pk>/pred', views.CycleAgingView.as_view(), name='prediction'),
]