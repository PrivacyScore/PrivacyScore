from django.conf.urls import url

from privacyscore.frontend import views

app_name = 'frontend'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^browse/$', views.browse, name='browse'),
    url(r'^contact/$', views.contact, name='contact'),
    url(r'^info/$', views.info, name='info'),
    url(r'^legal/$', views.legal, name='legal'),
    url(r'^list/create/$', views.scan_list, name='scan_list'),
    url(r'^list/(?P<scan_list_id>\d+)/$', views.view_scan_list,
        name='view_scan_list'),
    url(r'^site/(?P<site_id>\d+)/$', views.view_site, name='view_site'),
    url(r'^site/(?P<site_id>\d+)/screenshot$', views.site_screenshot, name='site_screenshot'),
    url(r'^login/$', views.login, name='login'),
    url(r'^lookup/$', views.lookup, name='lookup'),
    url(r'^scan/$', views.scan, name='scan'),
    url(r'^third_parties/$', views.third_parties, name='third_parties'),
    url(r'^user/$', views.user, name='user'),
]
