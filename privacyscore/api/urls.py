from django.conf.urls import url

from privacyscore.api import views

app_name = 'api'
urlpatterns = [
    url(r'^ShowLists/$', views.get_scan_lists, name='get_scan_lists'),
    url(r'^ShowList/(?P<token>\w+)/$', views.get_scan_list, name='get_scan_list'),
    url(r'^SaveList/$', views.save_scan_list, name='save_scan_list'),
    url(r'^UpdateList/$', views.update_scan_list, name='update_scan_list'),
    url(r'^DeleteList/(?P<token>\w+)/$', views.delete_scan_list, name='delete_scan_list'),
    url(r'^GetListID/(?P<token>\w+)/$', views.get_scan_list_id, name='get_scan_list_id'),
    url(r'^GetToken/(?P<scan_list_id>\w+)/$', views.get_token, name='get_token'),
    url(r'^Search/$', views.search_scan_lists, name='search_scan_lists'),
    url(r'^ScanList/$', views.scan_scan_list, name='scan_scan_list'),
    url(r'^SaveSite/$', views.save_site, name='save_site'),
    url(r'^site/(?P<site_id>\d+)/scan_groups/$', views.scan_groups_by_site,
        name='scan_groups_by_site'),
    url(r'^list/(?P<list_id>\d+)/scan_groups/$', views.scan_groups_by_scan_list,
        name='scan_groups_by_scan_list'),
    url(r'^scan/(?P<scan_id>\d+)/result/$', views.scan_result, name='scan_result'),
    url(r'^scan_group/(?P<scan_group_id>\d+)/results/$', views.scan_group_results, name='scan_group_results'),
]
