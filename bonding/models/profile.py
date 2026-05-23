from django.db import models
from django.utils import timezone
from .user import User
from .interest import Interest
from .preference import Preference
import uuid


class Profile(models.Model):
    GENDER_MALE = "male"
    GENDER_FEMALE = "female"
    GENDER_NON_BINARY = "non_binary"
    GENDER_FLUID = "fluid"
    GENDER_OTHER = "other"

    ORIENTATION_STRAIGHT = "straight"
    ORIENTATION_GAY = "gay"
    ORIENTATION_BISEXUAL = "bisexual"
    ORIENTATION_ASEXUAL = "asexual"
    ORIENTATION_PANSEXUAL = "pansexual"
    ORIENTATION_OTHER = "other"

    VERIFICATION_PENDING = "pending"
    VERIFICATION_APPROVED = "approved"
    VERIFICATION_REJECTED = "rejected"

    PREMIUM_FREE = "free"
    PREMIUM_PLUS = "plus"
    PREMIUM_GOLD = "gold"
    PREMIUM_PLATINUM = "platinum"

    INTENT_SERIOUS = "serious"
    INTENT_CASUAL = "casual"
    INTENT_FRIENDSHIP = "friendship"
    INTENT_EXPLORING = "exploring"

    choices_gender = [
        (GENDER_MALE, "Masculino"),
        (GENDER_FEMALE, "Feminino"),
        (GENDER_NON_BINARY, "Nao-binario"),
        (GENDER_FLUID, "Genero fluido"),
        (GENDER_OTHER, "Outro"),
    ]
    choices_orientation = [
        (ORIENTATION_STRAIGHT, "Heterossexual"),
        (ORIENTATION_GAY, "Homossexual"),
        (ORIENTATION_BISEXUAL, "Bissexual"),
        (ORIENTATION_ASEXUAL, "Assexual"),
        (ORIENTATION_PANSEXUAL, "Pansexual"),
        (ORIENTATION_OTHER, "Outro"),
    ]
    verification_choices = [
        (VERIFICATION_PENDING, "Pendente"),
        (VERIFICATION_APPROVED, "Aprovado"),
        (VERIFICATION_REJECTED, "Rejeitado"),
    ]
    premium_choices = [
        (PREMIUM_FREE, "Free"),
        (PREMIUM_PLUS, "Plus"),
        (PREMIUM_GOLD, "Gold"),
        (PREMIUM_PLATINUM, "Platinum"),
    ]
    relationship_intent_choices = [
        (INTENT_SERIOUS, "Relacionamento serio"),
        (INTENT_CASUAL, "Casual"),
        (INTENT_FRIENDSHIP, "Amizade"),
        (INTENT_EXPLORING, "Descobrindo"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    bio = models.TextField(blank=True, null=True)
    occupation = models.CharField(max_length=120, blank=True)
    education = models.CharField(max_length=120, blank=True)
    location = models.ForeignKey("Location", on_delete=models.SET_NULL, blank=True, null=True)
    gender = models.CharField(max_length=20, choices=choices_gender)
    sexual_orientation = models.CharField(max_length=20, choices=choices_orientation)
    course = models.CharField(max_length=100)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(blank=True, null=True)
    show_age = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=verification_choices,
        default=VERIFICATION_PENDING,
    )
    premium_tier = models.CharField(
        max_length=20,
        choices=premium_choices,
        default=PREMIUM_FREE,
    )
    relationship_intent = models.CharField(
        max_length=20,
        choices=relationship_intent_choices,
        default=INTENT_EXPLORING,
    )
    spotify_track_id = models.CharField(max_length=64, blank=True)
    spotify_track_name = models.CharField(max_length=255, blank=True)
    spotify_artist_name = models.CharField(max_length=255, blank=True)
    spotify_track_url = models.URLField(blank=True)
    spotify_album_image_url = models.URLField(blank=True)
    spotify_preview_url = models.URLField(blank=True)
    accent_color = models.CharField(max_length=7, default="#D71D29")
    min_preferred_age = models.PositiveIntegerField(default=18)
    max_preferred_age = models.PositiveIntegerField(default=99)
    max_distance_km = models.PositiveIntegerField(default=50)
    allow_video_calls = models.BooleanField(default=True)
    allow_date_suggestions = models.BooleanField(default=False)
    is_invisible_mode = models.BooleanField(default=False)
    interests = models.ManyToManyField(Interest, related_name="perfis", blank=True)
    preferences = models.ManyToManyField(
        Preference,
        related_name="perfis_com_preferencia",
        blank=True,
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.name}"
