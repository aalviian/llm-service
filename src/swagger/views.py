from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.views import SpectacularSwaggerView

from config.models import authenticate_julo_user


@method_decorator(csrf_exempt, name="dispatch")
class JuloLoginView(View):
    """Custom login view for JuloDB authentication"""

    template_name = "swagger/login.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")

        julo_user = authenticate_julo_user(username, password)
        if julo_user:
            # Create session for authenticated user
            request.session["julo_user_id"] = julo_user.id
            request.session["julo_username"] = julo_user.username
            return redirect("swagger:docs")

        return render(request, self.template_name, {"error": "Invalid credentials"})


class JuloLogoutView(View):
    """Logout view for JuloDB authenticated users"""

    def get(self, request):
        # Clear JuloDB session data
        request.session.pop("julo_user_id", None)
        request.session.pop("julo_username", None)
        request.session.flush()

        # Redirect to login page
        return redirect("swagger:login")


class SecureSwaggerView(SpectacularSwaggerView):
    """Swagger UI that requires JuloDB authentication"""

    template_name = "swagger/docs.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("julo_user_id"):
            return redirect("swagger:login")
        return super().dispatch(request, *args, **kwargs)
