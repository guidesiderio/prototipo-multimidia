from django.contrib import admin

from .models import Midia


@admin.register(Midia)
class MidiaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "dono", "criado_em")
    list_filter = ("tipo", "criado_em")
    search_fields = ("titulo", "descricao")
