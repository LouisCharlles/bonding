from django.contrib import admin
from .models import (
    Connection,
    ConsentRecord,
    Conversation,
    DateSuggestionFeedback,
    Interest,
    LegalDocumentVersion,
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
    PasswordResetToken,
    PushDevice,
    Report,
    Story,
    StoryReaction,
    StoryView,
    Subscription,
    Block,
    User,
    VerificationSelfie,
    VerificationToken,
    VideoCallSession,
    Wallet,
    WalletLedger,
    RewardEvent,
    UnlockSession,
    UserLocationPing,
)


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    """Log de consentimento e append-only: mesmo no admin, nao pode ser
    editado ou apagado (a trigger de banco tambem bloqueia isso)."""

    list_display = ("id", "user", "consent_type", "action", "granted_at", "ip_address")
    list_filter = ("consent_type", "action")
    search_fields = ("user__email",)
    readonly_fields = [f.name for f in ConsentRecord._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LegalDocumentVersion)
class LegalDocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("id", "document_type", "version_label", "is_current", "effective_date")
    list_filter = ("document_type", "is_current")


@admin.register(DateSuggestionFeedback)
class DateSuggestionFeedbackAdmin(admin.ModelAdmin):
    """Tabela de metricas de pesquisa (TCC): sugestoes de local mostradas e
    usadas, com os scores deterministico e semantico (LLM) por lugar."""

    list_display = (
        "id",
        "conversation_id",
        "event_type",
        "place_name",
        "deterministic_score",
        "llm_score",
        "llm_rank",
        "source",
        "variant",
        "experiment_run_id",
        "round_id",
        "used_at",
        "created_at",
    )
    list_filter = ("event_type", "source", "variant", "created_at")
    search_fields = ("place_name", "conversation__id", "round_id", "experiment_run_id")
    readonly_fields = [f.name for f in DateSuggestionFeedback._meta.fields]


admin.site.register(User)
admin.site.register(Profile)
admin.site.register(Photo)
admin.site.register(Interest)
admin.site.register(Preference)
admin.site.register(Location)
admin.site.register(Connection)
admin.site.register(Match)
admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(MessageReaction)
admin.site.register(Notification)
admin.site.register(Report)
admin.site.register(PremiumPlan)
admin.site.register(Subscription)
admin.site.register(Block)
admin.site.register(Story)
admin.site.register(StoryReaction)
admin.site.register(StoryView)
admin.site.register(Wallet)
admin.site.register(WalletLedger)
admin.site.register(RewardEvent)
admin.site.register(UnlockSession)
admin.site.register(ProfileVerificationAttempt)
admin.site.register(VerificationSelfie)
admin.site.register(UserLocationPing)
admin.site.register(PushDevice)
admin.site.register(VideoCallSession)
admin.site.register(VerificationToken)
admin.site.register(PasswordResetToken)
