from django.test import TestCase

# Create your tests here.
import shutil
import tempfile
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from relecloud.models import Destination
from django.urls import reverse
from io import BytesIO
from PIL import Image

# Creamos un MEDIA_ROOT temporal para no ensuciar el repo
_TEMP_MEDIA = tempfile.mkdtemp()

##################################
### TESTS PARA LA PT2 ###
##################################

@override_settings(MEDIA_ROOT=_TEMP_MEDIA, MEDIA_URL="/media/")
class PT2DestinationImageTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEMP_MEDIA, ignore_errors=True)

    def _fake_png(self) -> bytes:
        # PNG válido (1x1). Suficiente para ImageField + Pillow.
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00"
            b"\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    def _real_png_file(self):
        """
        Devuelve un SimpleUploadedFile con un PNG REAL generado con Pillow.
        """
        buffer = BytesIO()
        image = Image.new("RGB", (1, 1))  # 1x1 pixel
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return SimpleUploadedFile(
            name="dest.png",
            content=buffer.read(),
            content_type="image/png",
        )


    def test_destination_detail_renders_img_when_image_exists(self):
        # Arrange: destino con imagen
        upload = SimpleUploadedFile(
            name="dest.png",
            content=self._fake_png(),
            content_type="image/png",
        )
        dest = Destination.objects.create(
            name="Barcelona",
            description="Test description",
            image=upload,
        )

        # Act: abrir el detalle usando get_absolute_url (usa 'destination_detail')
        resp = self.client.get(dest.get_absolute_url())

        # Assert: 200 OK y HTML contiene <img ...> apuntando a destination.image.url
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<img", html=False)
        self.assertIn(dest.image.url, resp.content.decode("utf-8"))

    def test_destination_detail_does_not_break_when_no_image(self):
        # Arrange: destino sin imagen
        dest = Destination.objects.create(
            name="Madrid",
            description="No image",
        )

        # Act
        resp = self.client.get(dest.get_absolute_url())

        # Assert: 200 OK y no aparece ruta típica de destino en media
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("/media/destinations/", resp.content.decode("utf-8"))

    def test_destination_create_with_image(self):
        upload = self._real_png_file()

        url = reverse("destination_form")  # si este name es el correcto para "crear"

        resp = self.client.post(
            url,
            data={
                "name": "Rome",
                "description": "Test",
                "image": upload,
            },
            follow=False,  # IMPORTANTE: primero sin follow para ver si redirige o no
        )

        # 1) Si no es 200/302, ya tenemos pista
        self.assertIn(resp.status_code, (200, 302), msg=f"Unexpected status: {resp.status_code}")

        # 2) Si devuelve 200, normalmente significa: formulario inválido o permisos
        if resp.status_code == 200:
            # Si la respuesta tiene un form en context, mostramos errores
            form = resp.context.get("form") if hasattr(resp, "context") and resp.context else None
            if form is not None:
                self.fail(f"Form invalid. Errors: {form.errors}")
            else:
                # Si no hay form, quizá es otra vista/plantilla
                self.fail("Response 200 but no form in context. Maybe wrong URL name/view?")

        # 3) Si redirige (302), entonces debería haberse creado
        self.assertTrue(
            Destination.objects.filter(name="Rome").exists(),
            msg="Destination was not created (DB has no 'Rome'). Check view/form and permissions.",
        )

        dest = Destination.objects.get(name="Rome")
        self.assertTrue(dest.image.name)
        self.assertTrue(dest.image.name.startswith("destinations/"))



