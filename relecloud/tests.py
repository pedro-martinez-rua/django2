from django.core import mail
from . import models
import shutil
import tempfile
from io import BytesIO

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from django.contrib.auth import get_user_model
from django.db.models import Avg

from .models import Destination, Cruise, Purchase, Review


_TEMP_MEDIA = tempfile.mkdtemp()
User = get_user_model()

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

# TESTS PT3
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
class PT3ReviewsTests(TestCase):
    def setUp(self):
        self.u_buyer = User.objects.create_user(username="buyer", password="pass12345")
        self.u_other = User.objects.create_user(username="other", password="pass12345")

        self.dest = Destination.objects.create(name="Mars", description="Red planet")
        self.cruise = Cruise.objects.create(name="Cruise1", description="C1")
        self.cruise.destinations.add(self.dest)

        Purchase.objects.create(user=self.u_buyer, cruise=self.cruise)

    def test_anonymous_cannot_open_destination_review_form(self):
        url = reverse("destination_review", args=[self.dest.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

    def test_logged_user_without_purchase_cannot_post_destination_review(self):
        self.client.login(username="other", password="pass12345")
        url = reverse("destination_review", args=[self.dest.id])
        resp = self.client.post(url, {"rating": 5, "comment": "Nice"})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Review.objects.filter(user=self.u_other, destination=self.dest).exists())

    def test_buyer_can_create_destination_review(self):
        self.client.login(username="buyer", password="pass12345")
        url = reverse("destination_review", args=[self.dest.id])
        resp = self.client.post(url, {"rating": 4, "comment": "Great"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Review.objects.filter(user=self.u_buyer, destination=self.dest, rating=4).exists())

    def test_buyer_can_update_same_destination_review_instead_of_duplicate(self):
        Review.objects.create(user=self.u_buyer, destination=self.dest, rating=2, comment="ok")
        self.client.login(username="buyer", password="pass12345")
        url = reverse("destination_review", args=[self.dest.id])
        self.client.post(url, {"rating": 5, "comment": "updated"})
        self.assertEqual(Review.objects.filter(user=self.u_buyer, destination=self.dest).count(), 1)
        self.assertEqual(Review.objects.get(user=self.u_buyer, destination=self.dest).rating, 5)

    def test_average_rating_is_correct_for_destination(self):
        Review.objects.create(user=self.u_buyer, destination=self.dest, rating=4)
        Review.objects.create(user=self.u_other, destination=self.dest, rating=2)
        avg = self.dest.reviews.aggregate(a=Avg("rating"))["a"]
        self.assertEqual(avg, 3)

    def test_buyer_can_review_cruise(self):
        self.client.login(username="buyer", password="pass12345")
        url = reverse("cruise_review", args=[self.cruise.id])
        resp = self.client.post(url, {"rating": 5, "comment": "Amazing"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Review.objects.filter(user=self.u_buyer, cruise=self.cruise, rating=5).exists())
        
    def test_purchase_creates_purchase_and_enables_cruise_review(self):
        self.client.login(username="other", password="pass12345")
        purchase_url = reverse("cruise_purchase", args=[self.cruise.id])

        resp = self.client.post(purchase_url)
        self.assertEqual(resp.status_code, 302)

        self.assertTrue(Purchase.objects.filter(user=self.u_other, cruise=self.cruise).exists())

        # ahora debe permitir review
        review_url = reverse("cruise_review", args=[self.cruise.id])
        resp2 = self.client.post(review_url, {"rating": 5, "comment": "ok"})
        self.assertEqual(resp2.status_code, 302)
        self.assertTrue(Review.objects.filter(user=self.u_other, cruise=self.cruise).exists())
