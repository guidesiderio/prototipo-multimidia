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
