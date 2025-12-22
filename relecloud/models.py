from django.db import models
from django.urls import reverse
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q

# Create your models here
class Destination(models.Model):
    name = models.CharField(
        unique=True,
        max_length=50,
        null=False,
        blank=False,
    )
    description = models.TextField(
        max_length=2000,
        null=False,
        blank=False
    )
    image = models.ImageField(
        upload_to="destinations/",
        null=True,
        blank=True
    )
    def __str__(self):
        return self.name
    def get_absolute_url(self):
        return reverse('destination_detail', kwargs={'pk': self.pk})

class Cruise(models.Model):
    name = models.CharField(
        unique=True,
        max_length=50,
        null=False,
        blank=False,
    )
    description = models.TextField(
        max_length=2000,
        null=False,
        blank=False
    )
    destinations = models.ManyToManyField(
        Destination,
        related_name='cruises'
    )
    def __str__(self):
        return self.name

class InfoRequest(models.Model):
    name = models.CharField(
        max_length=50,
        null=False,
        blank=False,
    )
    email = models.EmailField()
    notes = models.TextField(
        max_length=2000,
        null=False,
        blank=False
    )
    cruise = models.ForeignKey(
        Cruise,
        on_delete=models.PROTECT
    )
    
class Purchase(models.Model):
    """
    Minimal purchase record for PT3:
    A user purchases a cruise. This enables reviews.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchases")
    cruise = models.ForeignKey("Cruise", on_delete=models.CASCADE, related_name="purchases")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} -> {self.cruise} ({self.created_at})"


class Review(models.Model):
    """
    One review can be for either a Destination or a Cruise.
    Exactly one of destination/cruise must be set.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    destination = models.ForeignKey("Destination", null=True, blank=True, on_delete=models.CASCADE, related_name="reviews")
    cruise = models.ForeignKey("Cruise", null=True, blank=True, on_delete=models.CASCADE, related_name="reviews")

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    (Q(destination__isnull=False) & Q(cruise__isnull=True)) |
                    (Q(destination__isnull=True) & Q(cruise__isnull=False))
                ),
                name="review_exactly_one_target",
            ),
            models.UniqueConstraint(
                fields=["user", "destination"],
                condition=Q(destination__isnull=False),
                name="uniq_review_user_destination",
            ),
            models.UniqueConstraint(
                fields=["user", "cruise"],
                condition=Q(cruise__isnull=False),
                name="uniq_review_user_cruise",
            ),
        ]

    def __str__(self):
        target = self.destination or self.cruise
        return f"{self.user} - {target} - {self.rating}/5"
