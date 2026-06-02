# Protótipo 1: Fundação da Aplicação Web (base local)

> Documento de especificação e instruções para o Claude Code construir a base da
> aplicação. Cobre as Fases 1, 2 e 3 do plano: esqueleto do Django, modelo de
> usuário e as telas de registro, login, logout, dashboard e perfil. A
> infraestrutura AWS (VPC, EC2, deploy) NÃO faz parte deste documento e será
> feita depois.

## 1. Contexto

Disciplina: Tópicos em Engenharia de Software (Computação em Nuvem), UFPI, turma
2026.1, Prof. Armando Soares Sousa. Avaliação 2, 1º protótipo. Projeto em equipe
de 5 alunos.

A aplicação web final gerencia objetos multimídia (imagens, áudios e vídeos).
Neste 1º protótipo o foco é a fundação: autenticação e perfil de usuário. Upload
de multimídia, S3 e RDS entram em protótipos posteriores.

Requisitos funcionais do 1º protótipo (a base que este documento prepara):

1. Registro de novos usuários.
2. Login e logout.
3. Dashboard exibido após o usuário autenticar (menu de opções e acesso à edição de perfil).
4. Edição de perfil: editar informações e alterar senha.

Propriedades exigidas do usuário: nome completo, username, password, email,
imagem de perfil, descrição e data de criação.

## 2. Decisões técnicas (já fechadas, não alterar)

* Framework: Django, versão 5 ou superior.
* Banco de dados: SQLite (padrão do Django) neste protótipo. Não usar PostgreSQL agora.
* Isolamento de dependências: venv. Não usar Docker.
* Código e comentários em português do Brasil.
* Projeto Django chamado `config`. App principal chamado `usuarios`.
* Modelo de usuário customizado estendendo `AbstractUser`.
* Autenticação com as views nativas do Django (`LoginView`, `LogoutView`, `PasswordChangeView`).
* Templates renderizados no servidor (Django Templates), sem framework de frontend.

## 3. Estado atual do repositório

A estrutura pode já existir (projeto `config` e app `usuarios` criados, Django
instalado no venv). Se já existir, pule os comandos de criação do Passo 1 e
aplique apenas o que faltar. Se o repositório estiver vazio, execute tudo a
partir do Passo 1.

Importante: o modelo de usuário customizado precisa existir antes da primeira
migração ser aplicada. Se já houver migrações aplicadas com o usuário padrão do
Django (arquivo `db.sqlite3` populado), apague o `db.sqlite3` e as migrações em
`usuarios/migrations/` (exceto `__init__.py`) antes de migrar de novo.

## 4. Tarefas a executar

### Passo 1: esqueleto do projeto

Na pasta raiz do projeto, com o venv ativo:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "Django>=5.0" Pillow
pip freeze > requirements.txt
django-admin startproject config .
python manage.py startapp usuarios
```

O Pillow é necessário para o campo de imagem do Django (`ImageField`).

### Passo 2: modelo de usuário, admin e configurações

Crie o arquivo `usuarios/models.py` com este conteúdo:

```python
from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    # username, password, email e date_joined (data de criacao) ja vem do AbstractUser
    nome_completo = models.CharField("nome completo", max_length=150, blank=True)
    descricao = models.TextField("descricao", blank=True)
    foto_perfil = models.ImageField(
        "foto de perfil", upload_to="perfis/", blank=True, null=True
    )

    def __str__(self):
        return self.username
```

Crie o arquivo `usuarios/admin.py` com este conteúdo:

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


class UsuarioAdmin(UserAdmin):
    # adiciona os campos de perfil na tela de edicao do admin
    fieldsets = UserAdmin.fieldsets + (
        ("Perfil", {"fields": ("nome_completo", "descricao", "foto_perfil")}),
    )


admin.site.register(Usuario, UsuarioAdmin)
```

Em `config/settings.py`, faça três alterações. Não mexa no bloco `DATABASES`: o
padrão já aponta para o SQLite.

1. Adicione `"usuarios"` ao fim da lista `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # apps padrao do Django ...
    "usuarios",
]
```

2. No fim do arquivo, aponte o modelo de usuário customizado:

```python
AUTH_USER_MODEL = "usuarios.Usuario"
```

3. Também no fim do arquivo, configure onde as imagens enviadas ficam:

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

Crie um arquivo `.gitignore` na raiz com este conteúdo:

```
.venv/
__pycache__/
*.pyc
db.sqlite3
media/
.env
```

Aplique as migrações e crie um superusuário para validação:

```bash
python manage.py makemigrations usuarios
python manage.py migrate
python manage.py createsuperuser
```

### Passo 3: telas de registro, login, logout, dashboard e perfil

Esta etapa usa as views nativas de autenticação do Django e adiciona views
próprias para registro, dashboard e edição de perfil. Os templates ficam em
`usuarios/templates/usuarios/` e são renderizados no servidor.

#### 3.1 Configurações adicionais em `config/settings.py`

No fim do arquivo, adicione:

```python
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
```

#### 3.2 Formulários

Crie `usuarios/forms.py`:

```python
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario


class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True, label="email")

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("username", "nome_completo", "email")


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ("nome_completo", "email", "descricao", "foto_perfil")
```

#### 3.3 Views

Substitua o conteúdo de `usuarios/views.py` por:

```python
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
```

#### 3.4 Rotas do app

Crie `usuarios/urls.py`:

```python
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
```

#### 3.5 Rotas do projeto

Substitua o conteúdo de `config/urls.py` por:

```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("usuarios.urls")),
    # a raiz redireciona para o dashboard (que exige login)
    path("", RedirectView.as_view(pattern_name="dashboard")),
]

# serve os arquivos de media durante o desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

#### 3.6 Templates

Crie a pasta `usuarios/templates/usuarios/` e os arquivos abaixo.

`base.html`:

```html
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block titulo %}Aplicação Multimídia{% endblock %}</title>
</head>
<body>
    <header>
        {% if user.is_authenticated %}
            <span>Olá, {{ user.username }}</span>
            <a href="{% url 'dashboard' %}">Dashboard</a>
            <a href="{% url 'editar_perfil' %}">Editar perfil</a>
            <form action="{% url 'logout' %}" method="post" style="display:inline">
                {% csrf_token %}
                <button type="submit">Sair</button>
            </form>
        {% endif %}
    </header>
    <main>
        {% block conteudo %}{% endblock %}
    </main>
</body>
</html>
```

`registro.html`:

```html
{% extends "usuarios/base.html" %}
{% block titulo %}Registro{% endblock %}
{% block conteudo %}
    <h1>Criar conta</h1>
    <form method="post">
        {% csrf_token %}
        {{ form.as_p }}
        <button type="submit">Registrar</button>
    </form>
    <p>Já tem conta? <a href="{% url 'login' %}">Entrar</a></p>
{% endblock %}
```

`login.html`:

```html
{% extends "usuarios/base.html" %}
{% block titulo %}Login{% endblock %}
{% block conteudo %}
    <h1>Entrar</h1>
    <form method="post">
        {% csrf_token %}
        {{ form.as_p }}
        <button type="submit">Entrar</button>
    </form>
    <p>Não tem conta? <a href="{% url 'registro' %}">Registre-se</a></p>
{% endblock %}
```

`dashboard.html`:

```html
{% extends "usuarios/base.html" %}
{% block titulo %}Dashboard{% endblock %}
{% block conteudo %}
    <h1>Dashboard</h1>
    {% if user.foto_perfil %}
        <img src="{{ user.foto_perfil.url }}" alt="foto de perfil" width="120">
    {% endif %}
    <p>Nome completo: {{ user.nome_completo }}</p>
    <p>Username: {{ user.username }}</p>
    <p>Email: {{ user.email }}</p>
    <p>Descrição: {{ user.descricao }}</p>
    <p>Membro desde: {{ user.date_joined }}</p>
    <ul>
        <li><a href="{% url 'editar_perfil' %}">Editar perfil</a></li>
        <li><a href="{% url 'alterar_senha' %}">Alterar senha</a></li>
    </ul>
{% endblock %}
```

`editar_perfil.html`:

```html
{% extends "usuarios/base.html" %}
{% block titulo %}Editar perfil{% endblock %}
{% block conteudo %}
    <h1>Editar perfil</h1>
    <form method="post" enctype="multipart/form-data">
        {% csrf_token %}
        {{ form.as_p }}
        <button type="submit">Salvar</button>
    </form>
    <p><a href="{% url 'alterar_senha' %}">Alterar senha</a></p>
{% endblock %}
```

`alterar_senha.html`:

```html
{% extends "usuarios/base.html" %}
{% block titulo %}Alterar senha{% endblock %}
{% block conteudo %}
    <h1>Alterar senha</h1>
    <form method="post">
        {% csrf_token %}
        {{ form.as_p }}
        <button type="submit">Salvar nova senha</button>
    </form>
{% endblock %}
```

#### 3.7 Observações de compatibilidade

* No Django 5, o logout só aceita requisição POST. Por isso o botão "Sair" no `base.html` fica dentro de um formulário com método post, e não como link.
* O formulário de edição de perfil usa `enctype="multipart/form-data"` porque envia a imagem.
* A raiz do site redireciona para o dashboard; um usuário não autenticado cai no login automaticamente por causa do `login_required`.

## 5. Critérios de aceitação

A entrega está correta quando:

1. `python manage.py migrate` roda sem erros.
2. `python manage.py createsuperuser` cria um superusuário com sucesso.
3. `python manage.py runserver` sobe o servidor em `http://127.0.0.1:8000/`.
4. Em `http://127.0.0.1:8000/admin/`, ao abrir um usuário, aparece a seção "Perfil" com os campos nome completo, descrição e foto de perfil.
5. Existe `requirements.txt` com pelo menos Django e Pillow.
6. Existe `.gitignore` ignorando `.venv/`, `db.sqlite3`, `media/` e caches do Python.
7. O arquivo `db.sqlite3` é gerado na raiz do projeto.
8. Em `/registro/`, criar uma conta funciona e já deixa o usuário autenticado, redirecionando para o dashboard.
9. Em `/login/`, autenticar com um usuário existente leva ao dashboard; o botão "Sair" encerra a sessão e volta para o login.
10. O dashboard mostra nome completo, username, email, descrição, data de criação e a foto (quando houver).
11. Em `/perfil/editar/`, salvar altera os dados e o upload de imagem funciona (a foto aparece no dashboard).
12. Em `/perfil/senha/`, alterar a senha funciona e mantém o usuário logado.
13. Acessar a raiz `/` redireciona para o dashboard; sem login, cai na tela de login.

## 6. Convenções de código

* Nomes de modelos, campos e funções em português quando fizer sentido.
* Comentários curtos e só onde agregam; nada de comentário óbvio.
* Seguir o estilo padrão do Django e o PEP 8.
* Não introduzir dependências além de Django e Pillow nesta etapa.

## 7. Fora de escopo nesta etapa (não implementar agora)

* PostgreSQL, RDS, S3 e upload de multimídia.
* Infraestrutura AWS: VPC, EC2, grupos de segurança, tabela de rotas, IP público.
* Auto scaling, balanceamento de carga e Gunicorn/Nginx (etapa de deploy).
* Estilização avançada: os templates desta etapa são funcionais e minimalistas, sem CSS elaborado.
