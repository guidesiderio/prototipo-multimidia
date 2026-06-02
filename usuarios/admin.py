from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


class UsuarioAdmin(UserAdmin):
    # adiciona os campos de perfil na tela de edicao do admin
    fieldsets = UserAdmin.fieldsets + (
        ("Perfil", {"fields": ("nome_completo", "descricao", "foto_perfil")}),
    )


admin.site.register(Usuario, UsuarioAdmin)
