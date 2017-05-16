from django.conf.urls import url

from privacyscore.api import views

app_name = 'api'
urlpatterns = [
    url(r'^ShowLists/$', views.get_lists, name='get_lists'),
    url(r'^ShowList/(?P<token>\w+)/$', views.get_list, name='get_list'),
    url(r'^SaveList/$', views.save_list, name='save_list'),
    url(r'^UpdateList/$', views.update_list, name='update_list'),
    url(r'^DeleteList/(?P<token>\w+)/$', views.delete_list, name='delete_list'),
    url(r'^GetListID/(?P<token>\w+)/$', views.get_list_id, name='get_list_id'),
    url(r'^GetToken/(?P<list_id>\w+)/$', views.get_token, name='get_token'),
    url(r'^Search/$', views.search_lists, name='search_lists'),
    url(r'^ScanList/$', views.scan_list, name='scan_list'),
    url(r'^SaveSite/$', views.save_site, name='save_site'),
    url(r'^site/(?P<site_id>\d+)/scan_groups/$', views.scan_groups_by_site,
        name='scan_groups_by_site'),
    url(r'^list/(?P<list_id>\d+)/scan_groups/$', views.scan_groups_by_list,
        name='scan_groups_by_list'),
]
