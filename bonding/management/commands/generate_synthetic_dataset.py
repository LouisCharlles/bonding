"""
Gera dataset sintético MULTI-TURNO de conversas em PT-BR com foco em:
- dates (explícitos e implícitos)
- universitários de São Luís - MA
- cultura local, praias, bares, shoppings, rolês
- gírias, emojis, ruído WhatsApp real
- emoção, tipo de relação, eventos locais
- contexto temporal/social

Cada linha do CSV é um turno (mensagem) de uma conversa.
Conversas são agrupadas por conversation_id.

Uso:
    python manage.py generate_synthetic_dataset
    python manage.py generate_synthetic_dataset --samples 5000
    python manage.py generate_synthetic_dataset --samples 5000 --noise-ratio 0.30
"""

import os
import random
import uuid

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

# =========================================================
# VOCABULÁRIO DE CONTEXTO
# =========================================================

EMOCOES = [
    "carente", "animado", "cansado", "apaixonado", "estressado",
    "entediado", "feliz", "triste", "saudoso", "empolgado",
]

TIPO_RELACAO = [
    "ficante", "namoro", "amizade", "colega_trabalho",
    "match_tinder", "ex", "contatinho", "crush",
]

GIRIAS = [
    "kkkk", "kkkkkkk", "mds", "slk", "vei", "mano",
    "misericórdia", "socorro", "😭", "🤣", "😩", "🥲",
    "aff", "oxe", "mah", "pai d'égua", "hahaha", "💀",
    "né não", "olha", "cara", "gente",
]

EVENTOS = [
    "no São João", "no arraial", "no reggae", "na prévia de carnaval",
    "na feirinha", "no show da Litorânea", "no bumba meu boi",
    "no rolê da Lagoa", "no forró universitário",
]

ROTINA = [
    "Tô indo no Mateus rapidinho.",
    "Passei raiva no trânsito hoje.",
    "Acabou energia aqui em casa.",
    "Meu iFood veio errado.",
    "Tô duro até o próximo pagamento.",
    "A chuva caiu bem na hora que saí.",
    "O calor hoje tá criminoso.",
    "Peguei ônibus lotado hoje cedo.",
    "O PIX caiu só agora.",
    "Passei a manhã resolvendo boleto.",
    "Minha internet caiu de novo.",
    "Fiquei preso no trânsito do Cohafuma.",
]

CONTEXTOS_TEMPORAIS = [
    "esse calor tá insuportável",
    "São Luís virou um forno",
    "essa chuva apareceu do nada",
    "o São João tá chegando",
    "o trânsito tá impossível hoje",
    "essa cidade tá parada hoje",
    "fim de semana chegou finalmente",
    "essa semana foi pesada demais",
]

RESPOSTAS_SIMPATICAS = [
    "Verdade demais 😩",
    "Kkkkk conta essa história",
    "Que situação hein",
    "Nem me fala",
    "Irmão que sofrimento",
    "Demais mesmo",
    "Eu entendo viu",
    "Que sufoco",
    "Boa sorte aí kkk",
    "Tô no mesmo barco",
    "Parece a minha semana",
    "Tá brincando",
    "Oxe que isso",
    "A vida é assim mesmo né",
]

CONFIRMACOES_DATE = [
    "Quero demais!",
    "Tô dentro ❤️",
    "Bora sim!",
    "Que horas?",
    "Já tô pronto(a)",
    "Topei!",
    "Simbora!",
    "Com você qualquer lugar",
    "Boa ideia! Me avisa",
    "Tô animado(a) já",
    "Nossa sim!!",
    "Tô esperando o horário",
]

# =========================================================
# PADRÕES DE DATE IMPLÍCITO
# =========================================================

PADROES_DATE_IMPLICITOS = [
    "Tava com saudade de conversar contigo.",
    "Tu sempre some quando eu quero sair.",
    "Hoje combinava muito uma praia.",
    "A gente ainda vai naquele lugar que tu falou.",
    "Tu me deve um sushi ainda.",
    "Queria companhia pra hoje.",
    "Tu toparia um rolê aleatório?",
    "Bora fugir da rotina hoje.",
    "Sextou e eu sem companhia.",
    "Tu anima um rolê sem planejamento?",
    "Hoje eu precisava ver alguém legal.",
    "Tu tem uma energia boa pra sair.",
    "Tava pensando que a gente podia se ver hoje.",
    "Saudade de sair com tu.",
    "A gente não se vê faz tempo.",
]

# =========================================================
# SAUDAÇÕES
# =========================================================

SAUDACOES = [
    "Oi, tudo bem?", "E aí?", "Falaa", "Opa", "Oi sumida",
    "E aí doido", "Tu tá onde?", "Como tu tá?", "Sobreviveu à semana?",
    "Oii", "Que fim levou tu?", "E aí meu patrão", "Meu Deus tu sumiu",
    "Oi criatura", "Bora viver?", "Partiu rolê hoje?", "E aí gata",
    "Opa meu consagrado", "Oi meu amor", "Ei sumiço",
]

INTENCOES = [
    "bora", "partiu", "topa", "anima", "vamo nessa", "queria muito",
    "tava pensando em", "o que acha de", "vamos", "tu anima",
    "simbora", "bora fazer", "partiu lançar", "vamo marcar",
]

ACOES = [
    "tomar um café", "comer sushi", "tomar um açaí", "comer hambúrguer",
    "tomar um drink", "ir num barzinho", "dar uma volta", "andar pela litorânea",
    "ver o pôr do sol", "assistir filme", "pegar um cinema", "lançar um sushi",
    "comer um lanche", "tomar um litrão", "ouvir música ao vivo", "jogar sinuca",
    "ir pra praia", "tomar sorvete", "comer pastel", "beber cerveja",
    "comer uma pizza", "tomar café gelado", "ver o mar", "ir no reggae",
    "dar rolê no shopping", "comer tapioca", "andar de carro sem rumo",
    "ver as luzes da cidade", "ficar conversando", "comer um camarão",
    "tomar um energético", "comer açaí na tigela",
]

# Mapeia ação → cuisine_or_amenity para ground truth
ACAO_TO_AMENITY = {
    "tomar um café": "café", "comer sushi": "sushi", "tomar um açaí": "açaí",
    "comer hambúrguer": "hambúrguer", "tomar um drink": "bar",
    "ir num barzinho": "bar", "dar uma volta": None, "andar pela litorânea": None,
    "ver o pôr do sol": None, "assistir filme": "cinema", "pegar um cinema": "cinema",
    "lançar um sushi": "sushi", "comer um lanche": "lanche",
    "tomar um litrão": "bar", "ouvir música ao vivo": "bar", "jogar sinuca": "bar",
    "ir pra praia": "praia", "tomar sorvete": "sorvete", "comer pastel": "pastel",
    "beber cerveja": "bar", "comer uma pizza": "pizza",
    "tomar café gelado": "café", "ver o mar": None, "ir no reggae": "reggae",
    "dar rolê no shopping": "shopping", "comer tapioca": "tapioca",
    "andar de carro sem rumo": None, "ver as luzes da cidade": None,
    "ficar conversando": None, "comer um camarão": "frutos do mar",
    "tomar um energético": "bar", "comer açaí na tigela": "açaí",
}

LOCAIS = [
    # Praias
    "na Praia do Calhau", "na Praia de São Marcos", "na Praia do Olho d'Água",
    "na Praia do Araçagy", "na extensão da Litorânea",
    # Avenidas / Pontos
    "na Litorânea", "na Lagoa da Jansen", "no Espigão Costeiro",
    "ali pela Avenida Holandeses", "no Centro Histórico", "no Reviver",
    "na Praça Gonçalves Dias", "na Feirinha São Luís",
    # Shoppings
    "no São Luís Shopping", "no Shopping da Ilha", "no Rio Anil Shopping",
    "no Golden Shopping", "na praça de alimentação do Rio Anil",
    # Bares
    "no Amsterdam Music Pub", "no Roots Bar", "no Seu Boteco",
    "no The Rock Pub", "no Talking Blues", "no Quintal da Vila",
    "no Bar do Léo", "no Chopp da Fábrica", "no Armazém", "no Buteko",
    # Restaurantes
    "no Coco Bambu", "no Cabana do Sol", "no Haruki", "no Fitó",
    "no Vignoli", "no Empório Fribal", "no Outback", "no Kitaro",
    # Cafés
    "no Buriteco Café", "na Coffeetown", "num café ali no Renascença",
    # Cultura
    "no Ceprama", "na Casa do Maranhão", "na Fonte do Ribeirão",
    # Genéricos
    "ali no Renascença", "ali pelo Calhau", "lá pras bandas do Turu",
    "lá no Cohatrac", "ali no Vinhais", "no Anjo da Guarda",
]

TEMPO = [
    "hoje?", "mais tarde?", "hoje à noite?", "amanhã?",
    "amanhã depois da aula?", "sexta depois da faculdade?",
    "nesse final de semana?", "sábado à tarde?", "domingo no fim da tarde?",
    "depois do estágio?", "depois da prova?", "quando tu sair da faculdade?",
    "hoje depois das 19h?", "sábado de noite?", "domingo de manhã?",
    "de madrugada mesmo kkkkk", "quando acabar esse calor infernal?",
]

PADROES_DATE = [
    "{saudacao} {intencao} {acao} {local} {tempo}",
    "{saudacao} bora {acao} {local}?",
    "{saudacao} topa {acao} {tempo}",
    "{saudacao} pensei da gente {acao} {local}",
    "{saudacao} partiu {local} hoje?",
    "{saudacao} depois da aula a gente podia {acao}",
    "{saudacao} tu anima ir {local} comigo?",
    "{saudacao} vamo nessa {acao} depois?",
    "{saudacao} queria muito {acao} contigo",
    "{saudacao} bora sair pra {acao}?",
    "{saudacao} simbora {local} mais tarde?",
    "{saudacao} tu vai fazer o que hoje? bora {acao}",
    "{saudacao} tava afim de {acao} {local}",
    "{saudacao} a gente podia aproveitar e {acao} {tempo}",
]

TIPOS_DATE = [
    "romantico", "casual", "praia", "bar", "universitario",
    "gastronomico", "cinema", "cultural", "shopping", "reggae", "role_noturno",
]

# =========================================================
# CONTEXTOS DE RUÍDO
# =========================================================

CURSOS = [
    "Direito", "Psicologia", "Arquitetura", "Medicina Veterinária", "Odontologia",
    "Administração", "Publicidade", "Design", "Engenharia Civil",
    "Engenharia de Software", "Ciência da Computação", "Estética",
    "Fisioterapia", "Nutrição", "Enfermagem", "Biomedicina", "Educação Física",
]

ASSUNTOS_POR_CURSO = {
    "Direito": ["Tô perdido em direito penal.", "A prova oral me destruiu.", "Tribunal do júri acabou comigo hoje.", "Passei o dia inteiro fazendo peça jurídica."],
    "Psicologia": ["A supervisão de estágio foi pesada hoje.", "Passei o dia lendo Freud.", "Tô cheio de relatório pra entregar.", "A aula de psicopatologia acabou comigo."],
    "Arquitetura": ["Passei a madrugada renderizando projeto.", "Minha maquete desmontou toda.", "AutoCAD travou bem na entrega.", "Professor pediu pra refazer a planta inteira."],
    "Odontologia": ["Passei o dia inteiro na clínica.", "Minhas costas tão destruídas de tanto atender.", "A aula prática acabou comigo."],
    "Medicina Veterinária": ["Hoje teve cirurgia no estágio.", "Passei o dia cuidando dos animais.", "Meu jaleco tá só sofrimento."],
    "Publicidade": ["Meu grupo mudou toda a campanha de última hora.", "Passei a madrugada editando vídeo.", "Apresentação da campanha foi hoje."],
    "Design": ["Passei horas escolhendo tipografia.", "Meu projeto ficou todo desalinhado.", "Illustrator travou no pior momento.", "Tô vivendo dentro do Figma."],
    "Administração": ["Tenho apresentação de plano de negócios amanhã.", "A planilha financeira acabou comigo.", "Tô atolado de trabalho da faculdade."],
    "Engenharia Civil": ["Cálculo estrutural tá impossível.", "A planta não fecha nunca.", "A obra do estágio tá uma loucura."],
    "Engenharia de Software": ["React acabou com meu psicológico.", "Passei horas corrigindo bug.", "Docker simplesmente não funciona.", "Meu deploy quebrou tudo."],
    "Ciência da Computação": ["Estrutura de dados tá me humilhando.", "Passei horas debugando código.", "A prova de algoritmo foi absurda."],
    "Fisioterapia": ["Passei o dia inteiro na clínica.", "Meu estágio tá puxado demais.", "Hoje teve atendimento direto."],
    "Nutrição": ["Passei horas montando dieta.", "A professora pediu análise nutricional completa.", "Nunca fiz tanto cálculo alimentar."],
    "Enfermagem": ["Plantão acabou comigo.", "Hoje foi corrido no estágio.", "Não consegui parar um minuto hoje."],
    "Biomedicina": ["Passei o dia no laboratório.", "A aula prática foi intensa hoje.", "Microscopia acabou comigo."],
    "Educação Física": ["Hoje teve aula prática o dia inteiro.", "Tô morto depois do treino.", "Meu estágio na academia foi puxado."],
    "Estética": ["Passei o dia atendendo cliente.", "A prática hoje foi cansativa.", "Meu estágio tá cheio essa semana."],
}

CONTEXTOS_GERAIS = [
    "CLT", "Autônomo", "Concurseiro", "Motorista de App", "Academia",
    "Gamer", "Família", "Relacionamento", "Desempregado", "Empreendedor",
    "Música", "Vida Adulta", "Delivery", "Servidor Público",
]

ASSUNTOS_GERAIS = {
    "CLT": ["Meu chefe passou demanda em pleno sábado.", "A firma acabou comigo hoje.", "Passei o dia inteiro em reunião.", "Saí do trabalho agora pouco."],
    "Autônomo": ["Cliente sumiu depois do orçamento.", "Trabalhar por conta própria cansa viu.", "Hoje foi puxado demais."],
    "Concurseiro": ["Passei o dia estudando português.", "Não aguento mais fazer questão.", "Tô vivendo de edital em edital."],
    "Motorista de App": ["O trânsito hoje tava impossível.", "Peguei corrida pro Araçagy e quase enlouqueci.", "Gasolina tá acabando comigo."],
    "Academia": ["Hoje o treino de perna destruiu minha existência.", "Meu personal quase me matou hoje.", "A academia tava lotada demais."],
    "Gamer": ["Passei raiva no ranked hoje.", "Meu time conseguiu perder uma partida impossível.", "O servidor caiu bem na hora da partida."],
    "Família": ["Minha mãe já tá perguntando quando vou casar.", "Passei o domingo inteiro em almoço de família.", "Hoje teve confusão lá em casa."],
    "Relacionamento": ["Relacionamento dá trabalho viu.", "A pessoa simplesmente sumiu.", "Não entendo sinais nenhum."],
    "Desempregado": ["Passei o dia mandando currículo.", "Fiz entrevista hoje.", "A vida adulta é cruel demais."],
    "Empreendedor": ["Passei o dia resolvendo problema de cliente.", "Meu financeiro tá um caos.", "Hoje foi só apagar incêndio."],
    "Música": ["Passei o dia ouvindo reggae.", "Queria muito ir pra um show.", "A playlist de hoje tá absurda."],
    "Vida Adulta": ["Adulto sofre demais com boleto.", "Passei o dia resolvendo coisa de banco.", "A vida adulta não tem tutorial."],
    "Delivery": ["Meu pedido demorou duas horas.", "Hoje só sobrevivi de iFood.", "Tô cansado até pra cozinhar."],
    "Servidor Público": ["Passei o dia atolado de processo.", "O sistema caiu de novo.", "Tô cansado dessa burocracia."],
}

ASSUNTOS_ALEATORIOS = [
    "A prova de cálculo acabou comigo.", "Professor simplesmente enlouqueceu hoje.",
    "Tô virando a noite fazendo projeto.", "A apresentação ficou horrível.",
    "Não aguento mais seminário.", "Meu grupo do trabalho sumiu.",
    "O trânsito da Holandeses tá impossível.", "São Luís tá quente num nível absurdo.",
    "A chuva caiu do nada hoje.", "Fiquei preso no trânsito do Cohafuma.",
    "Meu estágio tá acabando comigo.", "Preciso urgentemente dormir.",
    "Tô sobrevivendo só na base do café.", "Queria largar tudo e viver na praia.",
    "O reggae tava lotado ontem.", "O São João já tá chegando.",
    "Comi arroz de cuxá hoje no almoço.", "Nunca senti tanto calor assim.",
]

# =========================================================
# SUBSTITUIÇÕES WHATSAPP
# =========================================================

_WA_SUBSTITUTIONS = [
    ("você", "vc"), ("porque", "pq"), ("também", "tb"),
    ("estou", "tô"), ("está", "tá"), ("então", "aí"),
    ("muito", "mto"), ("obrigado", "vlw"), ("valeu", "vlw"),
    ("gente", "gnt"), ("quero", "qro"), ("fazer", "fzr"),
    ("para", "pra"), ("sobre", "sbre"),
]


# =========================================================
# COMANDO DJANGO
# =========================================================

class Command(BaseCommand):
    help = "Gera dataset sintético multi-turno regionalizado de São Luís - MA"

    def add_arguments(self, parser):
        parser.add_argument("--samples", type=int, default=5000)
        parser.add_argument(
            "--noise-ratio", type=float, default=0.30,
            help="Proporção de conversas de ruído puro (default: 0.30)"
        )

    def handle(self, *args, **options):
        samples = options["samples"]
        noise_ratio = max(0.0, min(1.0, options["noise_ratio"]))
        explicit_ratio = (1.0 - noise_ratio) * 0.64  # ~45% do total
        implicit_ratio = (1.0 - noise_ratio) * 0.36  # ~25% do total

        base_dir = os.path.join(settings.BASE_DIR, "data", "raw")
        os.makedirs(base_dir, exist_ok=True)
        out_path = os.path.join(base_dir, "dataset_bonding_sintetico.csv")

        self.stdout.write(self.style.WARNING(f"Gerando {samples} conversas..."))
        rows = []
        for _ in range(samples):
            r = random.random()
            if r < explicit_ratio:
                rows.extend(self._generate_multi_turn_date("explicita"))
            elif r < explicit_ratio + implicit_ratio:
                rows.extend(self._generate_multi_turn_date("implicita"))
            else:
                rows.extend(self._generate_multi_turn_noise())

        random.shuffle(rows)
        df = pd.DataFrame(rows)
        df.to_csv(out_path, index=False)

        total_convs = df["conversation_id"].nunique()
        intent_dist = df.drop_duplicates("conversation_id")["intent_type"].value_counts().to_dict()
        self.stdout.write(self.style.SUCCESS(f"Salvo em: {out_path}"))
        self.stdout.write(f"Conversas: {total_convs} | Turnos totais: {len(df)}")
        self.stdout.write(f"Distribuição: {intent_dist}")
        self.stdout.write("\nExemplos:\n")
        sample_convs = df["conversation_id"].drop_duplicates().sample(min(3, total_convs))
        for cid in sample_convs:
            self.stdout.write(f"\n--- conversa {cid[:8]} ---")
            for _, row in df[df["conversation_id"] == cid].iterrows():
                self.stdout.write(f"  [{row['sender']}] {row['text']}")

    # =========================================================
    # GERADOR MULTI-TURNO — DATE
    # =========================================================

    def _generate_multi_turn_date(self, intent_type: str) -> list[dict]:
        conversation_id = str(uuid.uuid4())
        emotion = random.choice(EMOCOES)
        relation = random.choice(TIPO_RELACAO)
        use_event = random.random() < 0.25

        # Metadados do date (populados ao construir o turno final)
        acao = ""
        tempo_usado = ""
        local_usado = ""
        tipo_date = "none"
        amenity = None

        turns: list[tuple[str, str]] = []  # (sender, text)

        # --- Turnos de abertura (ruído/contexto: 1–3 turnos antes do date) ---
        num_context = random.randint(1, 3)
        sender = "A"
        for i in range(num_context):
            if i == 0:
                text = random.choice(SAUDACOES)
            elif use_event and i == 1:
                ctx = random.choice(CONTEXTOS_TEMPORAIS)
                evento = random.choice(EVENTOS)
                text = f"{ctx}, você vai {evento}?"
            else:
                if random.random() < 0.5:
                    text = random.choice(ROTINA)
                else:
                    ctx = random.choice(CONTEXTOS_TEMPORAIS)
                    text = ctx[0].upper() + ctx[1:] + "."
            turns.append((sender, self._whatsapp_noise(text)))
            sender = "B" if sender == "A" else "A"

            # Resposta simpática do outro lado
            if random.random() < 0.7:
                resp = random.choice(RESPOSTAS_SIMPATICAS)
                turns.append((sender, self._whatsapp_noise(resp)))
                sender = "B" if sender == "A" else "A"

        # --- Turno final: sugestão de date ---
        if intent_type == "explicita":
            acao = random.choice(ACOES)
            local_usado = random.choice(LOCAIS)
            tempo_usado = random.choice(TEMPO)
            amenity = ACAO_TO_AMENITY.get(acao)
            pattern = random.choice(PADROES_DATE)
            date_text = pattern.format(
                saudacao=random.choice(SAUDACOES),
                intencao=random.choice(INTENCOES),
                acao=acao,
                local=local_usado,
                tempo=tempo_usado,
            )
            tipo_date = self._infer_tipo_date(acao)
        else:
            date_text = random.choice(PADROES_DATE_IMPLICITOS)
            tipo_date = "casual"

        date_text = self._clean(self._whatsapp_noise(date_text))
        turns.append((sender, date_text))
        sender = "B" if sender == "A" else "A"

        # Confirmação opcional do outro lado
        if random.random() < 0.6:
            turns.append((sender, self._whatsapp_noise(random.choice(CONFIRMACOES_DATE))))

        # --- Montar linhas CSV ---
        has_event = int(use_event)
        rows = []
        total_turns = len(turns)
        for idx, (sndr, text) in enumerate(turns):
            rows.append({
                "conversation_id": conversation_id,
                "turn_index": idx,
                "sender": sndr,
                "text": text,
                "is_date_intent": 1,
                "intent_type": intent_type,
                "emotion": emotion,
                "relation_type": relation,
                "has_local_event": has_event,
                "tem_local": int(bool(local_usado)),
                "tem_tempo": int(bool(tempo_usado)),
                "tipo_date": tipo_date,
                "acao_usada": acao,
                "tempo_usado": tempo_usado.rstrip("?").strip(),
                "local_usado": local_usado,
                "amenity": amenity or "",
                "cidade": "São Luís",
                "stage": self._infer_stage(intent_type, idx, total_turns),
            })
        return rows

    # =========================================================
    # GERADOR MULTI-TURNO — RUÍDO
    # =========================================================

    def _generate_multi_turn_noise(self) -> list[dict]:
        conversation_id = str(uuid.uuid4())
        emotion = random.choice(EMOCOES)
        relation = random.choice(TIPO_RELACAO)

        turns: list[tuple[str, str]] = []
        sender = "A"
        num_turns = random.randint(3, 6)

        for i in range(num_turns):
            if i == 0:
                text = random.choice(SAUDACOES)
            else:
                usar_curso = random.random() < 0.5
                if usar_curso:
                    curso = random.choice(CURSOS)
                    text = random.choice(ASSUNTOS_POR_CURSO[curso])
                else:
                    ctx = random.choice(CONTEXTOS_GERAIS)
                    text = random.choice(ASSUNTOS_GERAIS[ctx])
            turns.append((sender, self._whatsapp_noise(text)))
            sender = "B" if sender == "A" else "A"

            # Resposta ocasional
            if random.random() < 0.65:
                resp = random.choice(RESPOSTAS_SIMPATICAS)
                turns.append((sender, self._whatsapp_noise(resp)))
                sender = "B" if sender == "A" else "A"

        rows = []
        total_turns = len(turns)
        for idx, (sndr, text) in enumerate(turns):
            rows.append({
                "conversation_id": conversation_id,
                "turn_index": idx,
                "sender": sndr,
                "text": text,
                "is_date_intent": 0,
                "intent_type": "none",
                "emotion": emotion,
                "relation_type": relation,
                "has_local_event": 0,
                "tem_local": 0,
                "tem_tempo": 0,
                "tipo_date": "none",
                "acao_usada": "",
                "tempo_usado": "",
                "local_usado": "",
                "amenity": "",
                "cidade": "São Luís",
                "stage": self._infer_stage("none", idx, total_turns),
            })
        return rows

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _whatsapp_noise(text: str) -> str:
        """Aplica ruído estilo WhatsApp ao texto."""
        # Substituições informais
        for formal, informal in _WA_SUBSTITUTIONS:
            if random.random() < 0.20:
                text = text.replace(formal, informal)

        # Lowercase parcial
        if random.random() < 0.20:
            text = text.lower()

        # Remove pontuação final
        if random.random() < 0.30 and text and text[-1] in ".!":
            text = text[:-1]

        # Repetição de letras finais (ex: muitooo, kkkkkk)
        if random.random() < 0.15 and len(text) > 3:
            idx = random.randint(len(text) - 3, len(text) - 1)
            text = text[:idx] + text[idx] * random.randint(2, 4) + text[idx + 1:]

        # Append de gíria/emoji
        if random.random() < 0.35:
            text = text.rstrip() + " " + random.choice(GIRIAS)

        return text.strip()

    @staticmethod
    def _clean(text: str) -> str:
        text = " ".join(text.split())
        text = text.replace("??", "?").replace("  ", " ")
        return text.strip()

    @staticmethod
    def _infer_stage(intent_type: str, turn_index: int, total_turns: int) -> str:
        """Derives a conversation-stage label deterministically from the
        existing intent_type ground truth, so no manual re-annotation is
        needed. Mirrors ConversationStageSnapshot.STAGE_CHOICES."""
        if intent_type == "none":
            return "quebra_gelo" if turn_index < total_turns / 2 else "rapport"
        if intent_type == "implicita":
            return "interesse_mutuo"
        return "pronto_para_role"  # explicita

    @staticmethod
    def _infer_tipo_date(acao: str) -> str:
        acao_lower = acao.lower()
        if any(w in acao_lower for w in ["praia", "mar", "litorânea", "pôr do sol"]):
            return "praia"
        if any(w in acao_lower for w in ["bar", "litrão", "cerveja", "drink", "reggae", "barzinho"]):
            return "bar"
        if any(w in acao_lower for w in ["cinema", "filme"]):
            return "cinema"
        if any(w in acao_lower for w in ["sushi", "pizza", "hambúrguer", "lanche", "camarão", "tapioca", "pastel"]):
            return "gastronomico"
        if any(w in acao_lower for w in ["café", "sorvete", "açaí"]):
            return "casual"
        if any(w in acao_lower for w in ["shopping"]):
            return "shopping"
        if any(w in acao_lower for w in ["museu", "teatro", "cultura"]):
            return "cultural"
        return "casual"
