from django.conf.urls import url

from privacyscore.api import views

app_name = 'api'
urlpatterns = [
    url(r'^list/$', views.get_scan_lists, name='get_scan_lists'),
    url(r'^list/search/$', views.search_scan_lists, name='search_scan_lists'),
    url(r'^list/by_token/(?P<token>\w+)/$', views.get_scan_list_by_token,
        name='get_scan_list_by_token'),
    url(r'^list/save/$', views.save_scan_list, name='save_scan_list'),
    url(r'^list/(?P<scan_list_id>\d+)/update/$', views.update_scan_list,
        name='update_scan_list'),
    url(r'^list/(?P<scan_list_id>\d+)/delete/$', views.delete_scan_list,
        name='delete_scan_list'),
    url(r'^list/by_token/(?P<token>\w+)/$', views.get_scan_list_by_token, name='get_scan_list_by_token'),
    url(r'^list/(?P<scan_list_id>\d+)/scan/$', views.scan_scan_list, name='scan_scan_list'),
    url(r'^site/save/$', views.save_site, name='save_site'),
    url(r'^scan/(?P<scan_id>\d+)/result/$', views.scan_result, name='scan_result'),
]
