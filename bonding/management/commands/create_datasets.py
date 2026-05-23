"""
Gera um dataset sintético de conversas em PT-BR com foco em:
- dates
- contexto universitário
- locais reais de São Luís - MA
- classificação supervisionada

Uso:
    python generate_mock.py
"""

import os
import random
import pandas as pd

# ============================================
# CONFIG
# ============================================

BASE_DIR = os.path.join(os.getcwd(), "data", "raw")

# ============================================
# DADOS BASE
# ============================================

SAUDACOES = [
    "Oi, tudo bem?",
    "E aí?",
    "Opa, sumida",
    "Falaa",
    "Oi, como cê tá?",
    "E aí, sobreviveu à faculdade?",
    "Tu tá livre hoje?",
    "Oii",
    "Bora fazer alguma coisa?",
    "Que fim levou tu?"
]

INTENCOES = [
    "tava pensando em",
    "bora",
    "partiu",
    "tu anima",
    "queria muito",
    "vamos",
    "o que acha de",
    "topa",
    "vamo nessa",
    "anima de"
]

ACOES = [
    "tomar um café",
    "comer um sushi",
    "pegar um cinema",
    "dar uma volta",
    "ver o pôr do sol",
    "tomar um açaí",
    "comer um hambúrguer",
    "tomar um drink",
    "ir num barzinho",
    "jogar sinuca",
    "assistir um filme",
    "andar pela litorânea",
    "comer alguma coisa",
    "tomar um litrão",
    "lançar um lanche",
    "ver música ao vivo"
]

LOCAIS = [
    "na Litorânea",
    "no São Luís Shopping",
    "no Shopping da Ilha",
    "no Rio Anil Shopping",
    "no Golden Shopping",
    "lá no Chico Discos",
    "no Amsterdam Music Pub",
    "no Armazém",
    "no Seu Boteco",
    "no Cabana do Sol",
    "no Coco Bambu",
    "lá no Haruki",
    "no Outback do Shopping da Ilha",
    "na praça de alimentação do São Luís Shopping",
    "lá na UFMA",
    "na UEMA",
    "no Reviver",
    "ali pelo Centro Histórico",
    "na Lagoa da Jansen",
    "na Praça Gonçalves Dias",
    "na Feirinha São Luís",
    "no Espigão Costeiro",
    "na Praia do Calhau",
    "na Praia de São Marcos",
    "lá no Roots Bar",
    "no Buriteco Café",
    "no Empório Fribal",
    "no Fitó",
    "no Vignoli"
]

TEMPO = [
    "hoje à noite?",
    "amanhã depois da aula?",
    "sexta depois da faculdade?",
    "nesse final de semana?",
    "mais tarde?",
    "quinta-feira?",
    "sábado à tarde?",
    "domingo no fim da tarde?",
    "hoje depois do estágio?",
    "amanhã de noite?",
    "depois da prova?",
    "quando tu sair da UFMA?"
]

ASSUNTOS_ALEATORIOS = [
    "A prova de cálculo acabou comigo.",
    "Tô virando a noite fazendo projeto.",
    "O SIGAA caiu de novo kkkkk",
    "Professor surtou hoje na aula.",
    "Tu viu o calor que tá fazendo em São Luís?",
    "Passei 40 minutos preso no trânsito da Holandeses.",
    "Preciso urgentemente de um café.",
    "Meu estágio tá me destruindo.",
    "Tô travado num bug faz horas.",
    "A internet da UFMA simplesmente morreu hoje.",
    "Queria estar dormindo agora.",
    "Essa semana tá puxada demais."
]

TIPOS_DATE = [
    "romantico",
    "casual",
    "happy_hour",
    "praia",
    "universitario",
    "cinema",
    "gastronomico"
]

# ============================================
# PADRÕES DE FRASE
# ============================================

PADROES_DATE = [
    "{saudacao} {intencao} {acao} {local} {tempo}",
    "{saudacao} {intencao} {acao} {tempo}",
    "{saudacao} {acao} {local} {tempo}",
    "{saudacao} tu anima {acao} {local}?",
    "{saudacao} pensei da gente {acao} {tempo}",
    "{saudacao} bora {local} mais tarde?",
    "{saudacao} vamo nessa {acao} {local}",
    "{saudacao} topa {acao} depois da aula?",
]

PADROES_RUIDO = [
    "{saudacao} {assunto}",
    "{assunto}",
    "{saudacao} {assunto} kkkkk",
    "{assunto} sério",
]

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def limpar_texto(texto):
    texto = " ".join(texto.split())
    texto = texto.replace("??", "?")
    texto = texto.replace("?.", "?")
    return texto.strip()


def gerar_frase_date():
    padrao = random.choice(PADROES_DATE)

    frase = padrao.format(
        saudacao=random.choice(SAUDACOES),
        intencao=random.choice(INTENCOES),
        acao=random.choice(ACOES),
        local=random.choice(LOCAIS),
        tempo=random.choice(TEMPO)
    )

    frase = limpar_texto(frase)

    return {
        "text": frase,
        "is_date": 1,
        "tipo_date": random.choice(TIPOS_DATE),
        "tem_local": int(any(loc in frase for loc in LOCAIS)),
        "tem_tempo": int(any(tmp in frase for tmp in TEMPO))
    }


def gerar_frase_ruido():
    padrao = random.choice(PADROES_RUIDO)

    frase = padrao.format(
        saudacao=random.choice(SAUDACOES),
        assunto=random.choice(ASSUNTOS_ALEATORIOS)
    )

    frase = limpar_texto(frase)

    return {
        "text": frase,
        "is_date": 0,
        "tipo_date": "nenhum",
        "tem_local": 0,
        "tem_tempo": 0
    }


# ============================================
# GERAÇÃO DO DATASET
# ============================================

def generate_dataset(num_samples=3000):
    dados = []

    for _ in range(num_samples):

        # 70% date
        if random.random() < 0.7:
            dados.append(gerar_frase_date())

        # 30% ruído
        else:
            dados.append(gerar_frase_ruido())

    random.shuffle(dados)

    return dados


# ============================================
# MAIN
# ============================================

def main():

    os.makedirs(BASE_DIR, exist_ok=True)

    out_path = os.path.join(
        BASE_DIR,
        "dataset_bonding_sintetico.csv"
    )

    print("Gerando dataset sintético...")

    dados = generate_dataset(5000)

    df = pd.DataFrame(dados)

    df.to_csv(out_path, index=False)

    print(f"\nSucesso! {len(df)} mensagens geradas.")
    print(f"Arquivo salvo em:\n{out_path}")

    print("\nExemplos:\n")
    print(df.sample(10).to_string(index=False))


if __name__ == "__main__":
    main()