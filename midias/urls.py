from django.urls import path

from . import views

app_name = "midias"

urlpatterns = [
    path("midias/", views.lista, name="lista"),
    path("midias/nova/", views.criar, name="criar"),
    path("midias/<int:pk>/", views.detalhe, name="detalhe"),
    path("midias/<int:pk>/editar/", views.editar, name="editar"),
    path("midias/<int:pk>/excluir/", views.excluir, name="excluir"),
]
