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
