from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from .views import SecureSwaggerView, JuloLoginView, JuloLogoutView

app_name = 'swagger'

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SecureSwaggerView.as_view(url_name="swagger:schema"), name="docs"),
    path("login/", JuloLoginView.as_view(), name="login"),
    path("logout/", JuloLogoutView.as_view(), name="logout"),
]