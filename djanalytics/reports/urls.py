from django.conf.urls import url
from djanalytics.reports.views import (
    audience_overview,
    browser_detail,
    device_detail,
    device_overview,
    ecommerce_overview,
    page_overview,
)

urlpatterns = [
    url(r'^audience_overview/$', audience_overview, name='audience_overview'),
    url(r'^device_overview/$', device_overview, name='device_overview'),
    url(r'^ecommerce_overview/$', ecommerce_overview, name='ecommerce_overview'),
    url(r'^page_overview/$', page_overview, name='page_overview'),
    url(r'^device_detail/$', device_detail, name='device_detail'),
    url(r'^browser_detail/$', browser_detail, name='browser_detail'),
]
