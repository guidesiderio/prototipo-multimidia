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
