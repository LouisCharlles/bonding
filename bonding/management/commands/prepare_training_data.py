"""
Lê o CSV sintético gerado por generate_synthetic_dataset, reconstrói
as conversas multi-turno e exporta JSONL de fine-tuning do Gemini.

Saídas:
    data/gemini_train.jsonl
    data/gemini_val.jsonl
    data/gemini_test.jsonl
    data/enriched_keywords.json  (análise de co-ocorrência opcional)

Uso:
    python manage.py prepare_training_data
    python manage.py prepare_training_data --input meu_dataset.csv --min-turns 3
"""
import json
import os
import random
import re
from collections import Counter

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

from bonding.services.conversation_analysis import INTEREST_MAP, detect_interests_from_text
from bonding.services.gemini import _INTENT_PROMPT, _STAGE_PROMPT

RAW_DIR = os.path.join(settings.BASE_DIR, "data", "raw")
OUT_DIR = os.path.join(settings.BASE_DIR, "data")

SEED = 42

STOPWORDS = {
    "de", "a", "o", "e", "é", "do", "da", "dos", "das", "em", "um", "uma",
    "para", "com", "por", "que", "se", "na", "no", "ao", "à", "eu", "você",
    "ele", "ela", "nos", "nós", "me", "te", "lhe", "isso", "este", "essa",
    "mas", "ou", "não", "sim", "já", "só", "bem", "mais", "como", "até",
    "então", "muito", "tudo", "aqui", "lá", "ser", "ter", "ir", "vir",
    "vc", "tb", "pq", "né", "kk", "kkk",
}


class Command(BaseCommand):
    help = "Converte dataset sintético para JSONL de fine-tuning do Gemini"

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            default="dataset_bonding_sintetico.csv",
            help="Nome do arquivo CSV em data/raw/ (default: dataset_bonding_sintetico.csv)",
        )
        parser.add_argument(
            "--min-turns", type=int, default=2,
            help="Número mínimo de turnos por conversa para incluir (default: 2)",
        )
        parser.add_argument(
            "--train-ratio", type=float, default=0.80,
            help="Proporção de treino (default: 0.80)",
        )
        parser.add_argument(
            "--task", choices=["intent", "stage", "both"], default="intent",
            help="Qual tarefa exportar: intent (binário legado), stage (estágio+interesses) ou both (default: intent)",
        )

    def handle(self, *args, **options):
        input_path = os.path.join(RAW_DIR, options["input"])
        if not os.path.exists(input_path):
            self.stderr.write(self.style.ERROR(
                f"Arquivo não encontrado: {input_path}\n"
                "Execute 'python manage.py generate_synthetic_dataset' primeiro."
            ))
            return

        os.makedirs(OUT_DIR, exist_ok=True)

        df = pd.read_csv(input_path)
        self.stdout.write(f"Linhas carregadas: {len(df)} | Conversas: {df['conversation_id'].nunique()}")

        task = options["task"]

        if task in ("intent", "both"):
            examples = self._build_examples(df, options["min_turns"])
            self.stdout.write(f"Exemplos de intent gerados: {len(examples)}")
            if examples:
                self._write_splits(examples, "gemini", options["train_ratio"], dist_key="intent")

        if task in ("stage", "both"):
            stage_examples = self._build_stage_examples(df, options["min_turns"])
            self.stdout.write(f"Exemplos de stage gerados: {len(stage_examples)}")
            if stage_examples:
                self._write_splits(stage_examples, "gemini_stage", options["train_ratio"], dist_key="stage")

        self._export_enriched_keywords(df)

    # =========================================================

    def _write_splits(self, examples: list[dict], prefix: str, train_ratio: float, dist_key: str):
        random.seed(SEED)
        random.shuffle(examples)

        val_ratio = (1.0 - train_ratio) / 2
        n = len(examples)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        splits = {
            "train": examples[:n_train],
            "val": examples[n_train: n_train + n_val],
            "test": examples[n_train + n_val:],
        }

        for split_name, split_examples in splits.items():
            out_path = os.path.join(OUT_DIR, f"{prefix}_{split_name}.jsonl")
            with open(out_path, "w", encoding="utf-8") as fh:
                for ex in split_examples:
                    fh.write(json.dumps(ex, ensure_ascii=False) + "\n")
            label_dist = Counter(
                json.loads(ex["contents"][1]["parts"][0]["text"])[dist_key]
                for ex in split_examples
            )
            self.stdout.write(
                self.style.SUCCESS(f"  {split_name}: {len(split_examples)} exemplos → {out_path}")
                + f"  {dict(label_dist)}"
            )

        self.stdout.write(f"\nAmostra de treino ({prefix}):")
        for ex in splits["train"][:2]:
            user_text = ex["contents"][0]["parts"][0]["text"]
            model_text = ex["contents"][1]["parts"][0]["text"]
            self.stdout.write(f"\n[user] {user_text[:200]}...")
            self.stdout.write(f"[model] {model_text}")

    # =========================================================

    def _build_examples(self, df: pd.DataFrame, min_turns: int) -> list[dict]:
        examples = []
        for conv_id, group in df.groupby("conversation_id"):
            group = group.sort_values("turn_index")
            if len(group) < min_turns:
                continue

            # Reconstrói chat_history como lista de dicts {label, content}
            messages = [
                {"label": f"User {row['sender']}", "content": str(row["text"])}
                for _, row in group.iterrows()
            ]
            chat_history = "\n".join(f"{m['label']}: {m['content']}" for m in messages)
            prompt = _INTENT_PROMPT.format(chat_history=chat_history)

            # Ground truth baseado nos metadados da conversa
            meta = group.iloc[-1]  # metadados ficam iguais em todos os turnos
            label = self._build_label(meta)

            examples.append({
                "contents": [
                    {"role": "user", "parts": [{"text": prompt}]},
                    {"role": "model", "parts": [{"text": json.dumps(label, ensure_ascii=False)}]},
                ]
            })
        return examples

    def _build_label(self, meta) -> dict:
        intent_type = str(meta.get("intent_type", "none"))

        if intent_type == "none":
            return {
                "intent": "NONE",
                "confidence": 0,
                "entities": {"cuisine_or_amenity": None, "time": None},
            }

        # Jitter de confiança por tipo de intenção
        if intent_type == "explicita":
            confidence = random.randint(88, 98)
        else:  # implicita
            confidence = random.randint(75, 89)

        amenity = str(meta.get("amenity", "")) or None
        tempo = str(meta.get("tempo_usado", "")) or None

        return {
            "intent": "SUGGEST_DATE",
            "confidence": confidence,
            "entities": {
                "cuisine_or_amenity": amenity,
                "time": tempo,
            },
        }

    def _build_stage_examples(self, df: pd.DataFrame, min_turns: int) -> list[dict]:
        examples = []
        for conv_id, group in df.groupby("conversation_id"):
            group = group.sort_values("turn_index")
            if len(group) < min_turns:
                continue

            messages = [
                {"label": f"User {row['sender']}", "content": str(row["text"])}
                for _, row in group.iterrows()
            ]
            chat_history = "\n".join(f"{m['label']}: {m['content']}" for m in messages)
            prompt = _STAGE_PROMPT.format(chat_history=chat_history)

            meta = group.iloc[-1]
            label = self._build_stage_label(meta, chat_history)

            examples.append({
                "contents": [
                    {"role": "user", "parts": [{"text": prompt}]},
                    {"role": "model", "parts": [{"text": json.dumps(label, ensure_ascii=False)}]},
                ]
            })
        return examples

    def _build_stage_label(self, meta, chat_history: str) -> dict:
        stage = str(meta.get("stage", "quebra_gelo"))

        if stage in ("interesse_mutuo", "pronto_para_role"):
            stage_confidence = random.randint(80, 97)
        else:
            stage_confidence = random.randint(60, 84)

        interests = detect_interests_from_text(chat_history)
        tipo_date = str(meta.get("tipo_date", "none"))

        return {
            "stage": stage,
            "stage_confidence": stage_confidence,
            "interests": interests,
            "tipo_role": tipo_date if tipo_date != "none" else None,
        }

    def _export_enriched_keywords(self, df: pd.DataFrame):
        corpus = df["text"].dropna().str.lower().tolist()
        enriched = {}
        for interest, data in INTEREST_MAP.items():
            anchor_keywords = set(data["keywords"])
            co_terms: Counter = Counter()
            for sentence in corpus:
                if not any(kw in sentence for kw in anchor_keywords):
                    continue
                tokens = re.findall(r"\b[a-záàâãéêíóôõúç]{3,}\b", sentence)
                for token in tokens:
                    if token not in anchor_keywords and token not in STOPWORDS:
                        co_terms[token] += 1
            new_terms = [t for t, freq in co_terms.most_common(30) if freq >= 3]
            enriched[interest] = {
                "existing_keywords": data["keywords"],
                "suggested_new_keywords": new_terms,
                "label": data["label"],
            }

        out_path = os.path.join(OUT_DIR, "enriched_keywords.json")
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(enriched, fh, ensure_ascii=False, indent=2)
        self.stdout.write(self.style.SUCCESS(f"enriched_keywords.json → {out_path}"))
