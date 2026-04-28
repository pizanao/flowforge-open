"""URLs do FlowForge."""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve

urlpatterns = [

    path("api/", include("flowforge.api.urls")),
    # path('admin/doc/', include('django.contrib.admindocs.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    path("", admin.site.urls),
]
