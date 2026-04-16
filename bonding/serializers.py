from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    Block,
    Connection,
    Conversation,
    Interest,
    InstitutionDomain,
    Location,
    Match,
    Message,
    MessageReaction,
    Notification,
    Photo,
    Preference,
    PremiumPlan,
    Profile,
    ProfileVerificationAttempt,
    PushDevice,
    Report,
    RewardEvent,
    Story,
    StoryReaction,
    StoryView,
    Subscription,
    UnlockSession,
    VideoCallSession,
    VerificationSelfie,
    Wallet,
    WalletLedger,
)

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("username", None)

    def validate(self, attrs):
        attrs["email"] = attrs.get("email", "").lower().strip()
        data = super().validate(attrs)
        data["user"] = UserSummarySerializer(self.user).data
        return data


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "is_active", "date_joined"]
        read_only_fields = fields


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = "__all__"
        read_only_fields = ["id"]


class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = "__all__"
        read_only_fields = ["id"]


class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preference
        fields = "__all__"
        read_only_fields = ["id"]


class PhotoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Photo
        fields = [
            "id",
            "image",
            "image_url",
            "description",
            "order",
            "is_primary",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def get_image_url(self, obj):
        if not obj.image:
            return None
        url = obj.image.url
        if url.startswith("http://") or url.startswith("https://"):
            return url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url


class StoryViewSerializer(serializers.ModelSerializer):
    viewer = UserSummarySerializer(read_only=True)

    class Meta:
        model = StoryView
        fields = ["id", "viewer", "viewed_at"]
        read_only_fields = fields


class StoryReactionSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = StoryReaction
        fields = ["id", "user", "emoji", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class StorySerializer(serializers.ModelSerializer):
    author = UserSummarySerializer(read_only=True)
    reactions = StoryReactionSerializer(many=True, read_only=True)
    views = StoryViewSerializer(many=True, read_only=True)
    media_url = serializers.SerializerMethodField()
    viewers_count = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            "id",
            "author",
            "media_type",
            "media",
            "media_url",
            "caption",
            "visibility",
            "is_active",
            "expires_at",
            "created_at",
            "updated_at",
            "viewers_count",
            "views",
            "reactions",
        ]
        read_only_fields = ["id", "author", "created_at", "updated_at", "viewers_count", "views", "reactions"]

    def get_media_url(self, obj):
        if not obj.media:
            return None
        url = obj.media.url
        if url.startswith("http://") or url.startswith("https://"):
            return url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_viewers_count(self, obj):
        return obj.views.count()


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    photos = PhotoSerializer(many=True, read_only=True)
    location = LocationSerializer(read_only=True)
    interests = InterestSerializer(many=True, read_only=True)
    preferences = PreferenceSerializer(many=True, read_only=True)
    spotify_track = serializers.SerializerMethodField()
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
        source="location",
        write_only=True,
        required=False,
        allow_null=True,
    )
    interest_ids = serializers.PrimaryKeyRelatedField(
        queryset=Interest.objects.all(),
        many=True,
        source="interests",
        write_only=True,
        required=False,
    )
    preference_ids = serializers.PrimaryKeyRelatedField(
        queryset=Preference.objects.all(),
        many=True,
        source="preferences",
        write_only=True,
        required=False,
    )
    stats = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "uuid",
            "user",
            "name",
            "age",
            "bio",
            "occupation",
            "education",
            "location",
            "gender",
            "course",
            "sexual_orientation",
            "is_online",
            "show_age",
            "is_verified",
            "verification_status",
            "premium_tier",
            "relationship_intent",
            "spotify_track",
            "spotify_track_id",
            "spotify_track_name",
            "spotify_artist_name",
            "spotify_track_url",
            "spotify_album_image_url",
            "spotify_preview_url",
            "min_preferred_age",
            "max_preferred_age",
            "max_distance_km",
            "allow_video_calls",
            "allow_date_suggestions",
            "allow_study_match",
            "is_invisible_mode",
            "interests",
            "preferences",
            "photos",
            "location_id",
            "interest_ids",
            "preference_ids",
            "stats",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "uuid",
            "user",
            "is_verified",
            "verification_status",
            "premium_tier",
            "spotify_track",
            "created_at",
            "updated_at",
            "stats",
        ]

    def get_stats(self, obj):
        user = obj.user
        likes = Connection.objects.filter(
            from_user=user,
            status__in=[Connection.STATUS_LIKE, Connection.STATUS_SUPERLIKE],
        ).count()
        matches = Match.objects.filter(Q(user1=user) | Q(user2=user)).count()
        conversations = Conversation.objects.filter(
            Q(user1=user) | Q(user2=user)
        ).count()
        return {
            "likes_sent": likes,
            "matches": matches,
            "conversations": conversations,
        }

    def get_spotify_track(self, obj):
        if not obj.spotify_track_id or not obj.spotify_track_url:
            return None
        return {
            "id": obj.spotify_track_id,
            "name": obj.spotify_track_name,
            "artist": obj.spotify_artist_name,
            "url": obj.spotify_track_url,
            "image_url": obj.spotify_album_image_url,
            "preview_url": obj.spotify_preview_url,
        }

    def create(self, validated_data):
        interests = validated_data.pop("interests", [])
        preferences = validated_data.pop("preferences", [])
        profile = Profile.objects.create(**validated_data)
        if interests:
            profile.interests.set(interests)
        if preferences:
            profile.preferences.set(preferences)
        return profile


class BlockSerializer(serializers.ModelSerializer):
    blocker = UserSummarySerializer(read_only=True)

    class Meta:
        model = Block
        fields = ["id", "blocker", "blocked_user", "reason", "created_at"]
        read_only_fields = ["id", "blocker", "created_at"]

    def update(self, instance, validated_data):
        interests = validated_data.pop("interests", None)
        preferences = validated_data.pop("preferences", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if interests is not None:
            instance.interests.set(interests)
        if preferences is not None:
            instance.preferences.set(preferences)
        return instance


class DiscoverProfileSerializer(ProfileSerializer):
    distance_km = serializers.SerializerMethodField()

    class Meta(ProfileSerializer.Meta):
        fields = ProfileSerializer.Meta.fields + ["distance_km"]

    def get_distance_km(self, obj):
        request = self.context.get("request")
        current_profile = getattr(request.user, "profile", None) if request else None
        if not current_profile or not current_profile.location or not obj.location:
            return None
        if current_profile.location_id == obj.location_id:
            return 0
        return None


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())],
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
    )
    confirm_password = serializers.CharField(write_only=True, required=True)
    name = serializers.CharField(write_only=True, required=True)
    age = serializers.IntegerField(write_only=True, required=True, min_value=18)

    class Meta:
        model = User
        fields = ["id", "email", "password", "confirm_password", "name", "age"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "As senhas nao correspondem."}
            )
        email_domain = attrs["email"].split("@")[-1].lower().strip()
        if not InstitutionDomain.objects.filter(domain=email_domain, is_active=True, institution__is_active=True).exists():
            raise serializers.ValidationError(
                {"email": "Este e-mail institucional ainda nao esta aprovado para cadastro."}
            )
        return attrs

    def create(self, validated_data):
        name = validated_data.pop("name")
        age = validated_data.pop("age")
        validated_data.pop("confirm_password")

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )
        Profile.objects.create(
            user=user,
            name=name,
            age=age,
            gender=Profile.GENDER_OTHER,
            sexual_orientation=Profile.ORIENTATION_OTHER,
            course="",
        )
        return user


class ConnectionSerializer(serializers.ModelSerializer):
    from_user = UserSummarySerializer(read_only=True)
    to_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Connection
        fields = [
            "id",
            "from_user",
            "to_user",
            "status",
            "is_mutual",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "from_user", "is_mutual", "created_at", "updated_at"]


class ConversationSerializer(serializers.ModelSerializer):
    messages = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "user1",
            "user2",
            "created_at",
            "updated_at",
            "last_message",
            "other_user",
            "unread_count",
            "messages",
        ]
        read_only_fields = fields

    def get_messages(self, obj):
        include_messages = self.context.get("include_messages", False)
        if not include_messages:
            return []
        return MessageSerializer(obj.messages.all(), many=True, context=self.context).data

    def get_other_user(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        other = obj.user2 if obj.user1_id == request.user.id else obj.user1
        profile = getattr(other, "profile", None)
        if not profile:
            return UserSummarySerializer(other).data
        return {
            "id": other.id,
            "email": other.email,
            "profile": DiscoverProfileSerializer(profile, context=self.context).data,
        }

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request:
            return 0
        return obj.messages.filter(read=False).exclude(sender=request.user).count()


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSummarySerializer(read_only=True)
    conversation = serializers.PrimaryKeyRelatedField(
        queryset=Conversation.objects.all(),
        write_only=True,
    )
    reply_to_message = serializers.PrimaryKeyRelatedField(
        queryset=Message.objects.all(),
        required=False,
        allow_null=True,
    )
    story = serializers.PrimaryKeyRelatedField(
        queryset=Story.objects.all(),
        required=False,
        allow_null=True,
    )
    media_url = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender",
            "content",
            "message_type",
            "media",
            "media_url",
            "story",
            "reply_to_message",
            "is_view_once",
            "consumed_at",
            "is_system",
            "created_at",
            "read",
            "reactions",
        ]
        read_only_fields = ["id", "sender", "is_system", "created_at", "read"]

    def get_media_url(self, obj):
        if not obj.media:
            return None
        url = obj.media.url
        if url.startswith("http://") or url.startswith("https://"):
            return url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_reactions(self, obj):
        return MessageReactionSerializer(obj.reactions.all(), many=True).data

    def validate(self, attrs):
        is_view_once = attrs.get("is_view_once", False)
        media = attrs.get("media")
        message_type = attrs.get("message_type")

        if is_view_once and not media:
            raise serializers.ValidationError({"is_view_once": "Visualizacao unica so pode ser usada com midia."})
        if is_view_once and message_type not in [Message.TYPE_IMAGE, Message.TYPE_VIDEO]:
            raise serializers.ValidationError({"is_view_once": "Visualizacao unica so esta disponivel para imagem ou video."})
        return attrs


class MessageReactionSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = MessageReaction
        fields = ["id", "user", "emoji", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class MatchSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    conversation_id = serializers.IntegerField(source="conversation.id", read_only=True)

    class Meta:
        model = Match
        fields = [
            "id",
            "other_user",
            "conversation_id",
            "created_at",
            "is_active",
        ]
        read_only_fields = fields

    def get_other_user(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        other = obj.user2 if obj.user1_id == request.user.id else obj.user1
        return DiscoverProfileSerializer(other.profile, context=self.context).data


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ["id", "created_at", "recipient"]


class ReportSerializer(serializers.ModelSerializer):
    reporter = UserSummarySerializer(read_only=True)

    class Meta:
        model = Report
        fields = ["id", "reporter", "reported_user", "reason", "details", "status", "created_at"]
        read_only_fields = ["id", "reporter", "status", "created_at"]


class PremiumPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PremiumPlan
        fields = "__all__"
        read_only_fields = ["id"]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PremiumPlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=PremiumPlan.objects.filter(is_active=True),
        source="plan",
        write_only=True,
    )

    class Meta:
        model = Subscription
        fields = ["id", "plan", "plan_id", "status", "started_at", "expires_at"]
        read_only_fields = ["id", "status", "started_at", "expires_at"]


class WalletLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletLedger
        fields = ["id", "entry_type", "ribbons_delta", "hearts_delta", "rewinds_delta", "description", "metadata", "created_at"]
        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    entries = WalletLedgerSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = ["id", "ribbons_balance", "hearts_balance", "rewinds_balance", "updated_at", "entries"]
        read_only_fields = fields


class UnlockSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnlockSession
        fields = ["id", "target", "unlocked_until", "ribbons_spent", "created_at"]
        read_only_fields = fields


class RewardEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardEvent
        fields = ["id", "kind", "awarded_ribbons", "awarded_hearts", "created_at"]
        read_only_fields = fields


class ProfileVerificationAttemptSerializer(serializers.ModelSerializer):
    selfie_url = serializers.SerializerMethodField()

    class Meta:
        model = ProfileVerificationAttempt
        fields = [
            "id",
            "status",
            "score",
            "rejection_reason",
            "provider",
            "provider_payload",
            "created_at",
            "updated_at",
            "selfie_url",
        ]
        read_only_fields = ["id", "status", "score", "rejection_reason", "provider", "provider_payload", "created_at", "updated_at", "selfie_url"]

    def get_selfie_url(self, obj):
        selfie = getattr(obj, "selfie", None)
        if not selfie or not selfie.image:
            return None
        url = selfie.image.url
        request = self.context.get("request")
        if request and not url.startswith("http"):
            return request.build_absolute_uri(url)
        return url


class VerificationSelfieSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationSelfie
        fields = ["id", "attempt", "image", "brightness_score", "face_detected", "accessories_detected", "created_at"]
        read_only_fields = ["id", "brightness_score", "face_detected", "accessories_detected", "created_at"]


class PushDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushDevice
        fields = ["id", "token", "provider", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class VideoCallSessionSerializer(serializers.ModelSerializer):
    initiated_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = VideoCallSession
        fields = [
            "id",
            "conversation",
            "initiated_by",
            "room_name",
            "provider",
            "status",
            "started_at",
            "ended_at",
        ]
        read_only_fields = [
            "id",
            "initiated_by",
            "room_name",
            "provider",
            "status",
            "started_at",
            "ended_at",
        ]
