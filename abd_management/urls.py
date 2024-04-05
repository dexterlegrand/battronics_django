from django.urls import path, include

from . import views

app_name = 'abd_management'

urlpatterns = [
    path('', views.index, name='index'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('resources', views.Resources.as_view(), name="resources"),
    path('contact', views.contact, name='contact'),
    path('imprint', views.imprint, name='imprint'),
    path('disclaimer', views.disclaimer, name='disclaimer'),
    path('login', views.UserLogin.as_view(), name='login'),
    path('logout', views.UserLogout.as_view(), name='logout'),
    path('user', views.UserView.as_view(), name='user'),
]
