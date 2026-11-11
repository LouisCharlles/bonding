"""Seeds a small, fixed, idempotent set of fictional couples/conversations in
the real database for the TCC's date-suggestion experiment (see the plan's
item D). Creates only DB objects (User/Profile/Match/Conversation/Message/
UserLocationPing) — no Gemini/Overpass calls happen here, so the dataset can
be regenerated or wiped freely without spending API quota. That comes from
`run_date_experiment` instead.

All records are tagged with the `@tcc-experiment.bonding.local` email domain
so they can be found and removed with `--cleanup`.

The 4 hand-written SCENARIOS below (one per ConversationStageSnapshot stage,
plus the invented-venue bait scenario) are kept as qualitative, illustrative
cases and are always created. The optional `--extra=N` flag adds N further
procedurally-generated couples (varying stage template, interest hint,
first names and a small coordinate jitter around São Luís) on top of those
4, to enlarge the sample for the statistical metrics in report_date_experiment
(with N=4 every percentage is forced into 5% increments; a larger N gives
finer-grained, less coincidentally-round results). Generation is seeded
(`--seed`, default 42) for reproducibility.
"""
import random

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


# ---------------------------------------------------------------------------
# Geracao procedural de cenarios extras (--extra=N), para ampliar a amostra
# alem dos 4 cenarios qualitativos acima.
# ---------------------------------------------------------------------------

EXTRA_FIRST_NAMES = [
    "Marina", "Pedro", "Juliana", "Rafael", "Beatriz", "Thiago", "Camila", "Gustavo",
    "Larissa", "Felipe", "Isabela", "Rodrigo", "Patricia", "Andre", "Vanessa", "Leonardo",
    "Aline", "Marcelo", "Daniela", "Eduardo", "Renata", "Gabriel", "Natalia", "Vinicius",
    "Carolina", "Henrique", "Fernanda", "Igor", "Priscila", "Matheus", "Debora", "Caio",
    "Tatiana", "Bruno", "Luciana", "Daniel", "Amanda", "Victor", "Jessica", "Raul",
]

# Chaves alinhadas aos estagios reais de ConversationStageSnapshot.
STAGE_TEMPLATES = {
    "quebra_gelo": [
        [
            ("a", "Oi! Vi que a gente deu match agora, tudo bem?"),
            ("b", "Oi! Tudo ótimo, e você? Curti seu perfil"),
            ("a", "Tô bem sim! Você mora aqui em São Luís mesmo?"),
            ("b", "Moro sim, nasci e cresci aqui. E você?"),
        ],
        [
            ("a", "Boa noite! Gostei muito das suas fotos"),
            ("b", "Boa noite! Obrigado, que gentileza. E aí, como você tá?"),
            ("a", "Tô bem, só terminando de trabalhar aqui. Você trabalha com o quê?"),
            ("b", "Trabalho na área de tecnologia, e você?"),
        ],
        [
            ("a", "Opa, tudo certo? Vi que curtimos coisas parecidas"),
            ("b", "Fala! Tudo certo sim, que bom que deu match"),
            ("a", "Então, me conta um pouco sobre você"),
            ("b", "Sou bem tranquilo, gosto de sair bastante nos finais de semana"),
        ],
    ],
    "rapport": [
        [
            ("a", "Então me conta, o que você faz da vida?"),
            ("b", "Trabalho com design, e nas horas vagas gosto de sair e conhecer lugar novo"),
            ("a", "Sério? Eu também adoro conhecer lugar diferente"),
            ("b", "Haha então já temos assunto certo pra sempre puxar"),
            ("a", "Com certeza, adoro descobrir coisa nova na cidade"),
        ],
        [
            ("a", "Fiquei curiosa pra saber mais sobre você, pode falar um pouco?"),
            ("b", "Claro! Sou formado em administração, trabalho numa empresa daqui mesmo. E você?"),
            ("a", "Trabalho com marketing, adoro o que faço"),
            ("b", "Que legal, área bem dinâmica. E no tempo livre, o que você curte?"),
            ("a", "Gosto bastante de sair com amigos, conhecer lugar novo na cidade"),
        ],
    ],
    "interesse_mutuo": [
        [
            ("a", "Vc curte sair pra tomar algo com os amigos?"),
            ("b", "Demais, adoro um lugar com música ao vivo"),
            ("a", "Aaah que bom, eu também! Tô gostando muito de conversar contigo"),
            ("b", "Eu também tô curtindo bastante, vc é muito engraçada"),
            ("a", "Vc é gente boa também, fico até imaginando a gente saindo pra um rolê"),
        ],
        [
            ("a", "Sabe, tô gostando bastante de conversar com você"),
            ("b", "Eu também! Você é super fácil de conversar"),
            ("a", "Que bom saber disso. Acho que a gente combina bem"),
            ("b", "Concordo, já tô até pensando em marcar algo com você"),
        ],
    ],
    "pronto_para_role": [
        [
            ("a", "Já quero marcar de sair contigo esse fim de semana"),
            ("b", "Eu também, tô doido pra te ver pessoalmente"),
            ("a", "Queria um lugar bem legal, bacana mesmo, pra gente curtir"),
            ("b", "Entendi o clima, vou procurar um lugar assim pra gente"),
        ],
        [
            ("a", "Então, já tô doida pra te conhecer pessoalmente"),
            ("b", "Eu também! Vamos marcar algo esse fim de semana"),
            ("a", "Topo muito! Pode escolher o lugar, confio no seu gosto"),
            ("b", "Combinado, vou pensar em algo legal pra gente"),
        ],
    ],
}

# Uma frase natural por categoria de interesse (mesmas chaves de
# bonding.services.conversation_analysis.INTEREST_MAP), injetada na conversa
# para dar ao extrator de intenção um sinal textual de interesse real.
INTEREST_HINT_LINES = {
    "food": ("a", "Adoro experimentar restaurante novo, sou bem aventureira na comida"),
    "coffee": ("b", "Sou viciado em café, tomo umas três xícaras por dia kkk"),
    "bars": ("a", "Curto muito sair pra tomar uma cerveja com música ao vivo"),
    "outdoors": ("b", "Gosto bastante de parque, trilha, essas coisas ao ar livre"),
    "arts": ("a", "Adoro visitar museu e exposição de arte quando dá"),
    "movies": ("b", "Sou cinéfilo, vejo filme toda semana"),
    "nightlife": ("a", "Curto uma balada boa de vez em quando"),
    "sports": ("b", "Treino bastante, gosto de academia e corrida"),
    "shopping": ("a", "De vez em quando gosto de dar uma volta no shopping"),
}

_STAGE_KEYS = list(STAGE_TEMPLATES.keys())
_INTEREST_KEYS = list(INTEREST_HINT_LINES.keys())


def _build_extra_scenarios(n, seed=42):
    rng = random.Random(seed)
    scenarios = []
    for i in range(n):
        stage_key = _STAGE_KEYS[i % len(_STAGE_KEYS)]
        interest_key = _INTEREST_KEYS[i % len(_INTEREST_KEYS)]
        messages = list(rng.choice(STAGE_TEMPLATES[stage_key])) + [INTEREST_HINT_LINES[interest_key]]
        name_a = rng.choice(EXTRA_FIRST_NAMES)
        name_b = rng.choice(EXTRA_FIRST_NAMES)
        lat_offset = rng.uniform(-0.015, 0.015)
        lon_offset = rng.uniform(-0.015, 0.015)
        scenarios.append({
            "key": f"extra_{i:03d}_{stage_key}_{interest_key}",
            "user_a": (f"extra{i:03d}a", name_a),
            "user_b": (f"extra{i:03d}b", name_b),
            "coords_offset": (lat_offset, lon_offset),
            "messages": messages,
        })
    return scenarios


class Command(BaseCommand):
    help = "Gera (ou limpa) o dataset sintetico no banco para o experimento das 4 variantes (TCC)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help="Remove todos os usuarios/dados sinteticos do experimento (cascade) e sai.",
        )
        parser.add_argument(
            "--extra", type=int, default=0,
            help="Numero de cenarios adicionais gerados proceduralmente, alem dos 4 originais.",
        )
        parser.add_argument(
            "--seed", type=int, default=42,
            help="Semente aleatoria para a geracao procedural (reprodutibilidade).",
        )

    def handle(self, *args, **options):
        if options["cleanup"]:
            deleted, _ = User.objects.filter(email__endswith=f"@{EXPERIMENT_EMAIL_DOMAIN}").delete()
            self.stdout.write(self.style.WARNING(f"Removidos {deleted} registros (cascade)."))
            return

        all_scenarios = list(SCENARIOS)
        if options["extra"]:
            all_scenarios += _build_extra_scenarios(options["extra"], seed=options["seed"])

        for scenario in all_scenarios:
            with transaction.atomic():
                self._create_scenario(scenario)
        self.stdout.write(self.style.SUCCESS(f"{len(all_scenarios)} cenarios sinteticos prontos."))

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
