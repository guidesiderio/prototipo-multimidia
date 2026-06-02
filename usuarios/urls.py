from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from . import views

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="usuarios/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("perfil/editar/", views.editar_perfil, name="editar_perfil"),
    path(
        "perfil/senha/",
        auth_views.PasswordChangeView.as_view(
            template_name="usuarios/alterar_senha.html",
            success_url=reverse_lazy("dashboard"),
        ),
        name="alterar_senha",
    ),
]
