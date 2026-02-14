from django.contrib import admin
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.urls import path, include
from django.shortcuts import redirect

from config.swagger.schema import swagger_urlpatterns


urlpatterns = [
    path('', lambda request: redirect('/admin/', permanent=True)),
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
]

urlpatterns += [
    path('api/', include('apps.main.urls')),
]

urlpatterns += swagger_urlpatterns


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
                + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
