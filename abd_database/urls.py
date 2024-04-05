from django.urls import path, include
from rest_framework import routers

import abd_database.helpers.upload
from . import views, views_export, views_api

router = routers.DefaultRouter()
router.register(r'dataset', views_api.DatasetViewSet)
router.register(r'battery_types', views_api.BatteryTypeViewSet, basename='battery_types')
router.register(r'batteries', views_api.BatteryViewSet)
router.register(r'cell_tests', views_api.CellTestViewSet)
router.register(r'cycling_test', views_api.CyclingTestViewSet)
router.register(r'cycles', views_api.AggDataViewSet, basename='cycles')
router.register(r'cycling_rawdata', views_api.CyclingRawDataViewSet, basename='cyclingrawdata')
# router.register(r'upload', views_api.H5Upload, basename="upload")

app_name = 'abd_db'

urlpatterns = [
    path('api-auth/', include('rest_framework.urls')),
    path('batterytypes/<int:pk>/', views_api.BatteryTypeDetail.as_view(), name='batterytype-detail'),
    path('batteries/<int:pk>/', views_api.BatteryDetail.as_view(), name='battery-detail'),
    path('<int:ds>/', views.BatteryView.as_view(), name='index'),
    path('type/', views.BatteryTypeView.as_view(), name='type'),
    path('batt_<int:pk>/', views.BatteryDetail.as_view(), name='battery_detail'),
    path('batt_<int:battery_id>/download_cycles/', views_export.ExportAggData.as_view(), name='download_aggdata'),
    path('batt_<int:battery_id>/download_raw/', views_export.ExportRawData.as_view(), name='download_raw'),
    path('batt_<int:pk>/extend_tests/', views.ExtendTests.as_view(), name='extend_tests'),
    path('cycling/<int:cycling_test_id>/', views.cycling_test_detail, name='cycling_test_detail'),
    path('eis/<int:eis_test_id>/', views.eis_test_detail, name='eis_test_detail'),
    path('register_battery/', views.RegisterBattery.as_view(), name='register_battery'),
    path('upload_data/', views.FileFieldFormView.as_view(), name='upload_data'),
    path('job_queue/', views.JobViewQueue.as_view(), name='job_queue'),
    path('upload_duplicates/', abd_database.helpers.upload.upload_duplicates, name='upload_duplicates'),
    path('api/', include(router.urls)),
    path('job_queue/reupload/<int:file_id>/', views.Reuploadfile.as_view(), name='reupload_data_file'),
    path('register_dataset/', views.RegisterDataset.as_view(), name='register_dataset'),
    path('register_supplier/', views.RegisterSupplier.as_view(), name='register_supplier')
]
