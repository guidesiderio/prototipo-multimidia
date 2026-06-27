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
