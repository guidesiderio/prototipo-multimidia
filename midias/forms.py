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
