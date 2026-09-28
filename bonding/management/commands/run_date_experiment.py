"""Runs the 4 controlled pipeline variants (see
bonding/services/date_experiment_variants.py) over the synthetic dataset
created by `generate_date_experiment_dataset`, and persists the results into
DateSuggestionFeedback (source=experiment) tagged with a shared
experiment_run_id, so `report_date_experiment` can compare them.

Makes real calls to Gemini (4 variants x N conversations) and to the
Overpass API (1 call per conversation, shared across the 3 grounded
variants) — intentional, this measures real LLM behaviour, nothing here is
mocked.
"""
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from bonding.management.commands.generate_date_experiment_dataset import EXPERIMENT_EMAIL_DOMAIN
from bonding.models import Conversation, ConversationStageSnapshot, DateSuggestionFeedback, Message, UserLocationPing
from bonding.services.date_experiment_variants import (
    VARIANT_AI_PURE,
    VARIANT_DETERMINISTIC_PURE,
    VARIANT_HYBRID_FULL,
    VARIANT_HYBRID_SIMPLE_PROMPT,
    run_ai_pure,
    run_deterministic_pure,
    run_hybrid_control_simple_prompt,
    run_hybrid_full,
)
from bonding.services.external_integrations import IntegrationError, get_overpass_suggestions
from bonding.services.gemini import analyze_conversation_stage

RADIUS_KM = 100
USER_CITY = "São Luís - MA"


GEMINI_CALLS_PER_CONVERSATION = 4  # stage analysis + ai_pure + hybrid_full + hybrid_control


class Command(BaseCommand):
    help = "Roda as 4 variantes controladas (TCC) sobre o dataset sintetico e grava DateSuggestionFeedback."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Processa apenas as N primeiras conversas sinteticas (util para caber na cota diaria do Gemini).",
        )

    def handle(self, *args, **options):
        if not settings.GEMINI_API_KEY:
            raise CommandError(
                "GEMINI_API_KEY nao configurada — as variantes hibrida/controle/IA-pura "
                "nao fazem sentido sem chamadas reais ao Gemini."
            )

        conversations = Conversation.objects.filter(
            user1__email__endswith=f"@{EXPERIMENT_EMAIL_DOMAIN}",
            user2__email__endswith=f"@{EXPERIMENT_EMAIL_DOMAIN}",
        ).select_related("user1", "user2").order_by("id")

        if options["limit"]:
            conversations = conversations[:options["limit"]]

        conversations = list(conversations)
        if not conversations:
            raise CommandError(
                "Nenhuma conversa sintetica encontrada — rode "
                "`python manage.py generate_date_experiment_dataset` primeiro."
            )

        estimated_calls = len(conversations) * GEMINI_CALLS_PER_CONVERSATION
        self.stdout.write(
            f"{len(conversations)} conversa(s) -> ~{estimated_calls} chamadas Gemini "
            f"(free tier: 20/dia/modelo)."
        )

        experiment_run_id = str(uuid4())
        self.stdout.write(f"experiment_run_id={experiment_run_id}")

        for conversation in conversations:
            self._run_conversation(conversation, experiment_run_id)

        self.stdout.write(self.style.SUCCESS(
            f"Experimento concluido. experiment_run_id={experiment_run_id}"
        ))

    def _run_conversation(self, conversation, experiment_run_id):
        raw_messages = (
            Message.objects.filter(
                conversation=conversation, message_type=Message.TYPE_TEXT, is_system=False,
            )
            .order_by("created_at")
            .select_related("sender")
        )
        user1_id = conversation.user1_id
        messages = [
            {"label": "User A" if m.sender_id == user1_id else "User B", "content": m.content}
            for m in raw_messages
        ]
        if not messages:
            self.stdout.write(self.style.WARNING(f"Conversa {conversation.id} sem mensagens — pulando."))
            return

        stage_result = analyze_conversation_stage(messages)
        ConversationStageSnapshot.objects.update_or_create(
            conversation=conversation,
            defaults={
                "stage": stage_result.get("stage") or ConversationStageSnapshot.STAGE_QUEBRA_GELO,
                "stage_confidence": stage_result.get("stage_confidence") or 0,
                "interests": stage_result.get("interests") or [],
                "tipo_role": stage_result.get("tipo_role"),
            },
        )
        conversation_context = {
            "stage": stage_result.get("stage"),
            "interests": stage_result.get("interests", []),
            "tipo_role": stage_result.get("tipo_role"),
            "recent_messages": messages,
        }

        ping = (
            UserLocationPing.objects.filter(user_id__in=[conversation.user1_id, conversation.user2_id])
            .order_by("-created_at")
            .first()
        )
        if not ping:
            self.stdout.write(self.style.WARNING(f"Conversa {conversation.id} sem UserLocationPing — pulando."))
            return

        try:
            candidates = get_overpass_suggestions(
                ping.latitude, ping.longitude, radius_meters=RADIUS_KM * 1000,
            )
        except IntegrationError:
            self.stdout.write(self.style.WARNING(f"Conversa {conversation.id}: busca Overpass falhou — pulando."))
            candidates = []

        known_candidate_names = [c.get("name") for c in candidates if c.get("name")]

        ai_pure_places = run_ai_pure(conversation_context, USER_CITY, top_n=5)
        self._persist(
            conversation, experiment_run_id, VARIANT_AI_PURE, "ai_pure", ai_pure_places,
            extra_metadata={"known_candidate_names": known_candidate_names},
        )

        det_places = run_deterministic_pure(candidates, top_n=5)
        self._persist(conversation, experiment_run_id, VARIANT_DETERMINISTIC_PURE, "deterministic_pure", det_places)

        hybrid_places, hybrid_source = run_hybrid_full(candidates, conversation_context, top_n=5)
        self._persist(conversation, experiment_run_id, VARIANT_HYBRID_FULL, hybrid_source, hybrid_places)

        control_places, control_source = run_hybrid_control_simple_prompt(candidates, conversation_context, top_n=5)
        self._persist(
            conversation, experiment_run_id, VARIANT_HYBRID_SIMPLE_PROMPT, control_source, control_places,
        )

    def _persist(self, conversation, experiment_run_id, variant, ranking_source, places, extra_metadata=None):
        if not places:
            return
        round_id = str(uuid4())
        DateSuggestionFeedback.objects.bulk_create([
            DateSuggestionFeedback(
                conversation=conversation,
                place_name=place.get("name") or "",
                place_latitude=place.get("latitude"),
                place_longitude=place.get("longitude"),
                deterministic_score=place.get("deterministic_score"),
                llm_score=place.get("llm_score"),
                llm_rank=place.get("llm_rank"),
                metadata_completeness_score=place.get("metadata_completeness_score"),
                source=DateSuggestionFeedback.SOURCE_EXPERIMENT,
                variant=variant,
                experiment_run_id=experiment_run_id,
                round_id=round_id,
                metadata={
                    "ranking_source": ranking_source,
                    "llm_reason": place.get("llm_reason"),
                    "prompt_version": place.get("prompt_version"),
                    "prompt_position": place.get("prompt_position"),
                    "invalid_index_count": place.get("invalid_index_count"),
                    "radius_km": RADIUS_KM,
                    "declared_city": place.get("declared_city"),
                    "estimated_address": place.get("estimated_address"),
                    **(extra_metadata or {}),
                },
            )
            for place in places
        ])
