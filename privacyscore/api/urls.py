from django.conf.urls import url

from privacyscore.api import views

app_name = 'api'
urlpatterns = [
    url(r'^ShowLists/$', views.get_lists, name='get_lists'),
    url(r'^SaveList/$', views.save_list, name='save_list'),
    url(r'^UpdateList/$', views.update_list, name='update_list'),
    url(r'^SaveSite/$', views.save_site, name='save_site'),
]
