from django.test import TestCase
from django.urls import reverse
from django.core import mail
from . import models

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
