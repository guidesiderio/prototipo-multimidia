from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .forms import PerfilForm, RegistroForm


def registro(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)  # autentica logo apos o registro
            return redirect("dashboard")
    else:
        form = RegistroForm()
    return render(request, "usuarios/registro.html", {"form": form})


@login_required
def dashboard(request):
    return render(request, "usuarios/dashboard.html")


@login_required
def editar_perfil(request):
    if request.method == "POST":
        # request.FILES e necessario para receber a imagem enviada
        form = PerfilForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("dashboard")
    else:
        form = PerfilForm(instance=request.user)
    return render(request, "usuarios/editar_perfil.html", {"form": form})
