# Protótipo 2, Fase 1: app de mídias (CRUD local)

Documento de implementação para execução pelo Claude Code. Cobre o app
`midias` rodando **localmente** (SQLite + disco), atendendo os requisitos da
Avaliação 3 referentes à aplicação: CRUD de objetos multimídia, busca,
listagem, visualização/play e isolamento por usuário.

Fora do escopo desta fase (entram depois, sem alterar o modelo): S3 para os
binários, RDS/PostgreSQL no lugar do SQLite, ALB e Auto Scaling. A troca de
storage e de banco será de configuração, porque o modelo usa `FileField` e o
ORM abstrai o SQL.

## Pré-condições

- Repositório `prototipo-multimidia` já clonado, com o app `usuarios`
  funcionando (autenticação, perfil) e `AUTH_USER_MODEL = "usuarios.Usuario"`.
- Ambiente virtual ativo, dependências de `requirements.txt` instaladas.
- Django 5.2, banco SQLite local.

Nenhuma dependência nova nesta fase. O `requirements.txt` permanece como está.

## Resumo do que será feito

1. Criar o app `midias`.
2. Escrever os arquivos do app (modelo, form, views, urls, admin, templates, testes).
3. Editar 3 arquivos existentes: `config/settings.py`, `config/urls.py` e `usuarios/templates/usuarios/base.html`.
4. Gerar e aplicar a migração.
5. Rodar os testes e validar no navegador.

## Decisões fixadas no desenho aprovado

- Modelo único `Midia` com campo `tipo` (imagem, áudio, vídeo).
- `tipo` é deduzido pela extensão do arquivo no upload, validado contra lista branca.
- Isolamento por usuário via FK `dono`; acesso a mídia de outro usuário retorna 404.
- Editar mexe só em título e descrição; o binário não é trocado na edição.
- Teto de 50 MB por arquivo.
- Views por função com `@login_required`, seguindo o padrão do app `usuarios`.

---

## Passo 1: criar o app

```bash
python manage.py startapp midias
```

Isso gera o esqueleto. Os arquivos abaixo substituem ou complementam o que o
`startapp` criou. O `models.py`, `admin.py`, `tests.py` e `apps.py` já existem
após o `startapp`; substitua o conteúdo. O `forms.py`, `urls.py` e a pasta
`templates/midias/` precisam ser criados.

---

## Passo 2: arquivos do app

### `midias/models.py`

```python
from django.conf import settings
from django.db import models


class Midia(models.Model):
    class Tipo(models.TextChoices):
        IMAGEM = "imagem", "Imagem"
        AUDIO = "audio", "Áudio"
        VIDEO = "video", "Vídeo"

    dono = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="midias",
        verbose_name="dono",
    )
    titulo = models.CharField("título", max_length=200)
    descricao = models.TextField("descrição", blank=True)
    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices)
    arquivo = models.FileField("arquivo", upload_to="midias/")
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "mídia"
        verbose_name_plural = "mídias"

    def __str__(self):
        return self.titulo
```

O FK usa `settings.AUTH_USER_MODEL` para apontar para o `Usuario` customizado
sem importar o modelo direto.

### `midias/forms.py`

```python
import os

from django import forms

from .models import Midia

EXTENSOES = {
    Midia.Tipo.IMAGEM: {"jpg", "jpeg", "png", "gif", "webp"},
    Midia.Tipo.AUDIO: {"mp3", "wav", "ogg", "m4a"},
    Midia.Tipo.VIDEO: {"mp4", "webm", "mov"},
}
TAMANHO_MAXIMO = 50 * 1024 * 1024  # 50 MB em bytes


def detectar_tipo(nome_arquivo):
    """Retorna o tipo da mídia pela extensão, ou None se não suportada."""
    extensao = os.path.splitext(nome_arquivo)[1].lower().lstrip(".")
    for tipo, extensoes in EXTENSOES.items():
        if extensao in extensoes:
            return tipo
    return None


class MidiaCriarForm(forms.ModelForm):
    class Meta:
        model = Midia
        fields = ("titulo", "descricao", "arquivo")

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        if arquivo.size > TAMANHO_MAXIMO:
            raise forms.ValidationError("Arquivo acima de 50 MB. Envie um arquivo menor.")
        tipo = detectar_tipo(arquivo.name)
        if tipo is None:
            raise forms.ValidationError(
                "Extensão não suportada. Use imagem (jpg, jpeg, png, gif, webp), "
                "áudio (mp3, wav, ogg, m4a) ou vídeo (mp4, webm, mov)."
            )
        self._tipo_detectado = tipo
        return arquivo

    def save(self, commit=True):
        midia = super().save(commit=False)
        midia.tipo = self._tipo_detectado
        if commit:
            midia.save()
        return midia


class MidiaEditarForm(forms.ModelForm):
    class Meta:
        model = Midia
        fields = ("titulo", "descricao")
```

O `dono` não está no form; ele é setado na view a partir de `request.user`.

### `midias/views.py`

```python
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
```

O filtro `dono=request.user` em todas as consultas é o que garante o
isolamento. As views de objeto usam `get_object_or_404(..., dono=request.user)`,
então um usuário recebe 404 ao tentar acessar mídia de outro, sem vazar a
existência do registro.

### `midias/urls.py`

```python
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
```

### `midias/admin.py`

```python
from django.contrib import admin

from .models import Midia


@admin.register(Midia)
class MidiaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "dono", "criado_em")
    list_filter = ("tipo", "criado_em")
    search_fields = ("titulo", "descricao")
```

### `midias/apps.py`

Confirme que ficou assim (o `startapp` já gera; ajuste o nome se preciso):

```python
from django.apps import AppConfig


class MidiasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "midias"
```

---

## Passo 3: templates

Crie a pasta `midias/templates/midias/` e os arquivos abaixo. Todos estendem
`usuarios/base.html`, que já carrega o Bootstrap via CDN e renderiza as
mensagens.

### `midias/templates/midias/lista.html`

```html
{% extends "usuarios/base.html" %}
{% block titulo %}Minhas mídias{% endblock %}
{% block conteudo %}
<div class="d-flex justify-content-between align-items-center mb-3">
    <h1 class="h3 m-0">Minhas mídias</h1>
    <a href="{% url 'midias:criar' %}" class="btn btn-primary">Nova mídia</a>
</div>

<form method="get" class="row g-2 mb-4">
    <div class="col-sm-6">
        <input type="text" name="q" value="{{ q }}" class="form-control"
               placeholder="Buscar por título ou descrição">
    </div>
    <div class="col-sm-3">
        <select name="tipo" class="form-select">
            <option value="">Todos os tipos</option>
            {% for valor, rotulo in tipos %}
                <option value="{{ valor }}" {% if valor == tipo %}selected{% endif %}>{{ rotulo }}</option>
            {% endfor %}
        </select>
    </div>
    <div class="col-sm-3">
        <button type="submit" class="btn btn-outline-secondary w-100">Buscar</button>
    </div>
</form>

{% if midias %}
    <div class="row row-cols-1 row-cols-md-3 g-3">
        {% for midia in midias %}
            <div class="col">
                <div class="card h-100">
                    <div class="card-body">
                        <h2 class="h5 card-title">{{ midia.titulo }}</h2>
                        <span class="badge bg-secondary">{{ midia.get_tipo_display }}</span>
                        <p class="card-text mt-2 text-truncate">{{ midia.descricao }}</p>
                    </div>
                    <div class="card-footer bg-transparent">
                        <a href="{% url 'midias:detalhe' midia.pk %}" class="btn btn-sm btn-primary">Abrir</a>
                    </div>
                </div>
            </div>
        {% endfor %}
    </div>
{% else %}
    <p class="text-muted">Nenhuma mídia encontrada.</p>
{% endif %}
{% endblock %}
```

### `midias/templates/midias/detalhe.html`

```html
{% extends "usuarios/base.html" %}
{% block titulo %}{{ midia.titulo }}{% endblock %}
{% block conteudo %}
<div class="d-flex justify-content-between align-items-center mb-3">
    <h1 class="h3 m-0">{{ midia.titulo }}</h1>
    <div class="d-flex gap-2">
        <a href="{% url 'midias:editar' midia.pk %}" class="btn btn-outline-secondary btn-sm">Editar</a>
        <a href="{% url 'midias:excluir' midia.pk %}" class="btn btn-outline-danger btn-sm">Excluir</a>
    </div>
</div>

<p><span class="badge bg-secondary">{{ midia.get_tipo_display }}</span></p>

<div class="mb-3">
    {% if midia.tipo == "imagem" %}
        <img src="{{ midia.arquivo.url }}" alt="{{ midia.titulo }}" class="img-fluid rounded">
    {% elif midia.tipo == "audio" %}
        <audio controls src="{{ midia.arquivo.url }}" class="w-100"></audio>
    {% elif midia.tipo == "video" %}
        <video controls src="{{ midia.arquivo.url }}" class="w-100 rounded"></video>
    {% endif %}
</div>

{% if midia.descricao %}
    <p>{{ midia.descricao }}</p>
{% endif %}

<p class="text-muted small">Criado em {{ midia.criado_em }}</p>
<a href="{% url 'midias:lista' %}" class="btn btn-link px-0">Voltar para a lista</a>
{% endblock %}
```

### `midias/templates/midias/form.html`

Compartilhado por criar e editar. O `enctype` é necessário para o upload.

```html
{% extends "usuarios/base.html" %}
{% block titulo %}{{ titulo_pagina }}{% endblock %}
{% block conteudo %}
<h1 class="h3 mb-3">{{ titulo_pagina }}</h1>
<form method="post" enctype="multipart/form-data" class="col-md-8">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit" class="btn btn-primary">Salvar</button>
    <a href="{% url 'midias:lista' %}" class="btn btn-link">Cancelar</a>
</form>
{% endblock %}
```

Nota: `{{ form.as_p }}` renderiza sem as classes do Bootstrap. Se quiser o mesmo
acabamento dos formulários do app `usuarios`, dá para reaproveitar o parcial
`usuarios/_campos_form.html` aqui depois; nesta fase fica simples de propósito.

### `midias/templates/midias/confirmar_exclusao.html`

```html
{% extends "usuarios/base.html" %}
{% block titulo %}Excluir mídia{% endblock %}
{% block conteudo %}
<h1 class="h3 mb-3">Excluir mídia</h1>
<p>Tem certeza que deseja excluir <strong>{{ midia.titulo }}</strong>? Esta ação não pode ser desfeita.</p>
<form method="post">
    {% csrf_token %}
    <button type="submit" class="btn btn-danger">Excluir</button>
    <a href="{% url 'midias:detalhe' midia.pk %}" class="btn btn-link">Cancelar</a>
</form>
{% endblock %}
```

---

## Passo 4: testes

### `midias/tests.py`

```python
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Midia

Usuario = get_user_model()
MEDIA_TEMP = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_TEMP)
class MidiaTestes(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_TEMP, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.a = Usuario.objects.create_user(username="a", password="senha-forte-123")
        self.b = Usuario.objects.create_user(username="b", password="senha-forte-123")
        self.midia_a = Midia.objects.create(
            dono=self.a,
            titulo="Foto do A",
            tipo=Midia.Tipo.IMAGEM,
            arquivo=SimpleUploadedFile("a.png", b"conteudo", content_type="image/png"),
        )

    def test_usuario_nao_ve_midia_de_outro(self):
        self.client.login(username="b", password="senha-forte-123")
        resposta = self.client.get(reverse("midias:detalhe", args=[self.midia_a.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_usuario_nao_edita_midia_de_outro(self):
        self.client.login(username="b", password="senha-forte-123")
        resposta = self.client.get(reverse("midias:editar", args=[self.midia_a.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_lista_mostra_apenas_proprias(self):
        self.client.login(username="b", password="senha-forte-123")
        resposta = self.client.get(reverse("midias:lista"))
        self.assertNotContains(resposta, "Foto do A")

    def test_upload_extensao_invalida(self):
        self.client.login(username="a", password="senha-forte-123")
        arquivo = SimpleUploadedFile("virus.exe", b"x", content_type="application/octet-stream")
        resposta = self.client.post(
            reverse("midias:criar"),
            {"titulo": "Ruim", "descricao": "", "arquivo": arquivo},
        )
        self.assertEqual(resposta.status_code, 200)  # reexibe o form com erro
        self.assertEqual(Midia.objects.filter(titulo="Ruim").count(), 0)

    def test_busca_por_titulo(self):
        self.client.login(username="a", password="senha-forte-123")
        resposta = self.client.get(reverse("midias:lista"), {"q": "Foto"})
        self.assertContains(resposta, "Foto do A")
```

Os testes usam um `MEDIA_ROOT` temporário, então não sujam a pasta `media/` do
projeto.

---

## Passo 5: editar arquivos existentes

Três edições cirúrgicas. Em cada uma, localize o trecho `ANTES` e substitua
pelo `DEPOIS`.

### 5.1 `config/settings.py`, registrar o app

ANTES:
```python
    'usuarios',
]
```
DEPOIS:
```python
    'usuarios',
    'midias',
]
```

### 5.2 `config/urls.py`, incluir as rotas

ANTES:
```python
    path("", include("usuarios.urls")),
    # a raiz redireciona para o dashboard (que exige login)
    path("", RedirectView.as_view(pattern_name="dashboard")),
```
DEPOIS:
```python
    path("", include("usuarios.urls")),
    path("", include("midias.urls")),
    # a raiz redireciona para o dashboard (que exige login)
    path("", RedirectView.as_view(pattern_name="dashboard")),
```

As rotas de `midias` já carregam o prefixo `midias/` internamente, então o
`include` na raiz não conflita com a `RedirectView` (que casa só com o path vazio).

### 5.3 `usuarios/templates/usuarios/base.html`, item de menu

ANTES:
```html
                    <ul class="navbar-nav me-auto">
                        <li class="nav-item">
                            <a class="nav-link" href="{% url 'dashboard' %}">Dashboard</a>
                        </li>
```
DEPOIS:
```html
                    <ul class="navbar-nav me-auto">
                        <li class="nav-item">
                            <a class="nav-link" href="{% url 'dashboard' %}">Dashboard</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="{% url 'midias:lista' %}">Minhas mídias</a>
                        </li>
```

---

## Passo 6: migração, testes e validação

```bash
python manage.py makemigrations midias
python manage.py migrate
python manage.py test midias
python manage.py runserver
```

Checkpoint de validação manual (logado como um usuário comum):

1. Menu mostra "Minhas mídias"; o link abre a lista vazia.
2. "Nova mídia" envia uma imagem; redireciona para o detalhe e a imagem aparece.
3. Repetir com um mp3 (player de áudio) e um mp4 (player de vídeo).
4. Tentar enviar um `.exe` ou arquivo acima de 50 MB; o form recusa com mensagem de erro.
5. Buscar por um trecho do título e filtrar por tipo; a lista responde.
6. Editar título/descrição de uma mídia; o detalhe reflete a mudança.
7. Excluir uma mídia pela tela de confirmação; some da lista e o arquivo sai de `media/midias/`.
8. Criar um segundo usuário, fazer login com ele e confirmar que não vê nem acessa (404) as mídias do primeiro.

## Mapa de requisitos atendidos nesta fase

| Requisito da Avaliação 3 (item A) | Onde é atendido |
|-----------------------------------|-----------------|
| CRUD em objetos multimídia | views `criar`, `detalhe`, `editar`, `excluir` |
| Pesquisar objetos | view `lista` com parâmetro `q` |
| Listar objetos | view `lista` |
| Visualizar/play | `detalhe.html` renderiza por `tipo` |
| Segurança por usuário (isolamento) | FK `dono` + filtro em todas as consultas |

Escalonamento horizontal (ALB e Auto Scaling), RDS e S3 ficam para as fases
seguintes do Protótipo 2.

## Próxima fase (não implementar agora)

Integração com S3 via `django-storages` e `boto3`, configurada no setting
`STORAGES` do Django 5.2, com credenciais por IAM role anexada à EC2. O campo
`arquivo` continua `FileField`; muda só a configuração de storage.
