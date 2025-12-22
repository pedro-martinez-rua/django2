from django.core import mail
from . import models
import shutil
import tempfile
from io import BytesIO

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from relecloud.models import Destination

_TEMP_MEDIA = tempfile.mkdtemp()

# PT1 TESTS
@override_settings(
    # Media (aislado para tests)
    MEDIA_ROOT=_TEMP_MEDIA,
    MEDIA_URL="/media/",

    # Evitar redirecciones HTTPS en tests (tu CI usa DEBUG=False)
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,

    # Forzar storage local en tests aunque en prod uses AzureStorage
    DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
)
class InfoRequestEmailTest(TestCase):
    def setUp(self):
        # Create a Cruise instance for the test
        self.cruise = models.Cruise.objects.create(name="Test Cruise", description="Test Description")

    def test_info_request_sends_emails(self):
        response = self.client.post(reverse('info_request'), {
            'name': 'Test User',
            'email': 'testuser@example.com',
            'cruise': self.cruise.id,
            'notes': 'Test notes',
        })

        # Check redirect after form submission
        self.assertEqual(response.status_code, 302)

        # Check that two emails were sent
        self.assertEqual(len(mail.outbox), 2)

        # Verify email subjects
        self.assertEqual(mail.outbox[0].subject, "New information request")
        self.assertEqual(mail.outbox[1].subject, "Request received")


# PT2 TESTS
@override_settings(
    # Media (aislado para tests)
    MEDIA_ROOT=_TEMP_MEDIA,
    MEDIA_URL="/media/",

    # Evitar redirecciones HTTPS en tests (tu CI usa DEBUG=False)
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,

    # Forzar storage local en tests aunque en prod uses AzureStorage
    DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
)
class PT2DestinationImageTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEMP_MEDIA, ignore_errors=True)

    def _real_png_file(self):
        buffer = BytesIO()
        img = Image.new("RGB", (1, 1))
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return SimpleUploadedFile(
            name="dest.png",
            content=buffer.read(),
            content_type="image/png",
        )

    def test_destination_detail_renders_img_when_image_exists(self):
        upload = self._real_png_file()
        dest = Destination.objects.create(
            name="Barcelona",
            description="Test description",
            image=upload,
        )

        resp = self.client.get(dest.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertIn(dest.image.url, resp.content.decode("utf-8"))

    def test_destination_detail_does_not_break_when_no_image(self):
        dest = Destination.objects.create(
            name="Madrid",
            description="No image",
        )

        resp = self.client.get(dest.get_absolute_url())
        self.assertEqual(resp.status_code, 200)

    def test_destination_create_with_image(self):
        upload = self._real_png_file()
        url = reverse("destination_form")  # ajusta si el name cambia

        resp = self.client.post(
            url,
            data={"name": "Rome", "description": "Test", "image": upload},
            follow=False,
        )

        # En create normalmente esperamos redirect
        self.assertEqual(resp.status_code, 302)

        self.assertTrue(Destination.objects.filter(name="Rome").exists())
        dest = Destination.objects.get(name="Rome")
        self.assertTrue(dest.image.name)
        self.assertTrue(dest.image.name.startswith("destinations/"))
