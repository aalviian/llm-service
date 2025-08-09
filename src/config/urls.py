from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import NewHealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health-check/", NewHealthCheckView.as_view()),
    path("api/", include("autoreply.urls", namespace="autoreply")),
    path("swagger/api/", include("swagger.urls", namespace="swagger")),
]

if settings.DEBUG:
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
