from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MidiaCriarForm, MidiaEditarForm
from .models import Midia


@login_required
def lista(request):
    midias = Midia.objects.filter(dono=request.user)
    q = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "").strip()
    if q:
        midias = midias.filter(Q(titulo__icontains=q) | Q(descricao__icontains=q))
    if tipo in dict(Midia.Tipo.choices):
        midias = midias.filter(tipo=tipo)
    contexto = {
        "midias": midias,
        "q": q,
        "tipo": tipo,
        "tipos": Midia.Tipo.choices,
    }
    return render(request, "midias/lista.html", contexto)


@login_required
def detalhe(request, pk):
    midia = get_object_or_404(Midia, pk=pk, dono=request.user)
    return render(request, "midias/detalhe.html", {"midia": midia})


@login_required
def criar(request):
    if request.method == "POST":
        form = MidiaCriarForm(request.POST, request.FILES)
        if form.is_valid():
            midia = form.save(commit=False)
            midia.dono = request.user
            midia.save()
            messages.success(request, "Mídia criada com sucesso.")
            return redirect("midias:detalhe", pk=midia.pk)
    else:
        form = MidiaCriarForm()
    return render(request, "midias/form.html", {"form": form, "titulo_pagina": "Nova mídia"})


@login_required
def editar(request, pk):
    midia = get_object_or_404(Midia, pk=pk, dono=request.user)
    if request.method == "POST":
        form = MidiaEditarForm(request.POST, instance=midia)
        if form.is_valid():
            form.save()
            messages.success(request, "Mídia atualizada com sucesso.")
            return redirect("midias:detalhe", pk=midia.pk)
    else:
        form = MidiaEditarForm(instance=midia)
    return render(request, "midias/form.html", {"form": form, "titulo_pagina": "Editar mídia"})


@login_required
def excluir(request, pk):
    midia = get_object_or_404(Midia, pk=pk, dono=request.user)
    if request.method == "POST":
        midia.arquivo.delete(save=False)  # remove o binário do storage
        midia.delete()
        messages.success(request, "Mídia excluída.")
        return redirect("midias:lista")
    return render(request, "midias/confirmar_exclusao.html", {"midia": midia})
