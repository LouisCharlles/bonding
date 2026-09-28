"""Seeds a small, fixed, idempotent set of fictional couples/conversations in
the real database for the TCC's date-suggestion experiment (see the plan's
item D). Creates only DB objects (User/Profile/Match/Conversation/Message/
UserLocationPing) — no Gemini/Overpass calls happen here, so the dataset can
be regenerated or wiped freely without spending API quota. That comes from
`run_date_experiment` instead.

All records are tagged with the `@tcc-experiment.bonding.local` email domain
so they can be found and removed with `--cleanup`.

Kept to 4 scenarios (one per ConversationStageSnapshot stage, plus the
invented-venue bait scenario) so a full `run_date_experiment` run stays at
4 conversations x 4 Gemini calls each (stage analysis + ai_pure +
hybrid_full + hybrid_control) = 16 calls/day — comfortably under the Gemini
free tier's 20 requests/day/model quota, with margin for ad-hoc testing.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from bonding.models import Conversation, Match, Message, Profile, User, UserLocationPing

EXPERIMENT_EMAIL_DOMAIN = "tcc-experiment.bonding.local"

# São Luís-MA coordinates, with small per-couple jitter for realism.
_SAO_LUIS_BASE = (-2.5300, -44.3028)

SCENARIOS = [
    {
        "key": "quebra_gelo",
        "user_a": ("ana.slz", "Ana"),
        "user_b": ("bruno.slz", "Bruno"),
        "coords_offset": (0.000, 0.000),
        "messages": [
            ("a", "Oiii, tudo bem? Vi que a gente deu match agora rs"),
            ("b", "Oi Ana! Tudo sim, e você? Curti seu perfil"),
            ("a", "Tô bem! Vc é de São Luís mesmo?"),
            ("b", "Sou sim, nasci e cresci aqui"),
        ],
    },
    {
        "key": "rapport_cafe",
        "user_a": ("carla.slz", "Carla"),
        "user_b": ("diego.slz", "Diego"),
        "coords_offset": (0.003, -0.002),
        "messages": [
            ("a", "Then me conta, o que vc faz da vida?"),
            ("b", "Trampo com design, e nas horas vagas gosto de tomar um café bom"),
            ("a", "Sério? Eu AMO café, sou meio viciada kkkk"),
            ("b", "Haha então a gente já tem um assunto certo pra falar sempre"),
            ("a", "Com certeza, adoro descobrir cafeteria nova"),
        ],
    },
    {
        "key": "interesse_mutuo_bar",
        "user_a": ("elisa.slz", "Elisa"),
        "user_b": ("fabio.slz", "Fabio"),
        "coords_offset": (-0.004, 0.003),
        "messages": [
            ("a", "Vc curte sair pra beber uma cerveja com os amigos?"),
            ("b", "Demais, adoro um bar com música ao vivo"),
            ("a", "Aaah que bom, eu também! Tô gostando muito de conversar contigo"),
            ("b", "Eu também tô curtindo bastante, vc é muito engraçada"),
            ("a", "Vc é gente boa também, fico até imaginando a gente saindo pra um rolê"),
        ],
    },
    {
        # Textual bait for the ai_pure variant, which has no grounding in
        # real OSM data at all: asks for something specific and "chique" in
        # a real upscale São Luís neighborhood, to see if an ungrounded LLM
        # invents a plausible-sounding establishment that doesn't actually
        # exist there (checked against real Overpass candidates in
        # report_date_experiment.py's variant violation metric).
        "key": "pronto_para_role_invencao_local",
        "user_a": ("karina.slz", "Karina"),
        "user_b": ("lucas.slz", "Lucas"),
        "coords_offset": (0.001, -0.004),
        "messages": [
            ("a", "Lucas, já quero marcar de sair contigo esse fim de semana"),
            ("b", "Eu também Karina, tô doido pra te ver pessoalmente"),
            ("a", "Queria um lugar chique, tipo aqueles bares novos da Ponta d'Areia ou da Renascença, "
                  "com uma decoração toda especial"),
            ("b", "Entendi o clima que vc quer, vou procurar um lugar assim pra gente"),
            ("a", "Isso, algo bem diferenciado mesmo, que pouca gente conhece ainda"),
        ],
    },
]


class Command(BaseCommand):
    help = "Gera (ou limpa) o dataset sintetico no banco para o experimento das 4 variantes (TCC)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help="Remove todos os usuarios/dados sinteticos do experimento (cascade) e sai.",
        )

    def handle(self, *args, **options):
        if options["cleanup"]:
            deleted, _ = User.objects.filter(email__endswith=f"@{EXPERIMENT_EMAIL_DOMAIN}").delete()
            self.stdout.write(self.style.WARNING(f"Removidos {deleted} registros (cascade)."))
            return

        for scenario in SCENARIOS:
            with transaction.atomic():
                self._create_scenario(scenario)
        self.stdout.write(self.style.SUCCESS(f"{len(SCENARIOS)} cenarios sinteticos prontos."))

    def _create_scenario(self, scenario):
        lat = _SAO_LUIS_BASE[0] + scenario["coords_offset"][0]
        lon = _SAO_LUIS_BASE[1] + scenario["coords_offset"][1]

        user_a = self._get_or_create_user(*scenario["user_a"])
        user_b = self._get_or_create_user(*scenario["user_b"])
        users = {"a": user_a, "b": user_b}

        conversation, _ = Conversation.objects.get_or_create(user1=user_a, user2=user_b)
        Match.objects.get_or_create(
            user1=user_a, user2=user_b, defaults={"conversation": conversation},
        )
        UserLocationPing.objects.get_or_create(
            user=user_a, defaults={"latitude": lat, "longitude": lon},
        )
        UserLocationPing.objects.get_or_create(
            user=user_b, defaults={"latitude": lat, "longitude": lon},
        )

        if not Message.objects.filter(conversation=conversation).exists():
            for sender_key, text in scenario["messages"]:
                Message.objects.create(
                    conversation=conversation,
                    sender=users[sender_key],
                    content=text,
                    message_type=Message.TYPE_TEXT,
                )

    def _get_or_create_user(self, local_part, display_name):
        email = f"{local_part}@{EXPERIMENT_EMAIL_DOMAIN}"
        user, created = User.objects.get_or_create(
            email=email, defaults={"password": ""},
        )
        if created:
            user.set_password("tcc-experiment-not-a-real-password")
            user.save(update_fields=["password"])
            Profile.objects.create(
                user=user,
                name=display_name,
                age=27,
                gender=Profile.GENDER_OTHER,
                sexual_orientation=Profile.ORIENTATION_OTHER,
                course="Engenharia de Software",
            )
        return user
