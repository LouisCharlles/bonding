"""
Avalia o classificador de estágio/interesses via Gemini contra a heurística
legada de palavra-chave (INTEREST_MAP), usando o conjunto de teste gerado
por `prepare_training_data --task stage`.

Uso:
    python manage.py evaluate_stage_classifier
    python manage.py evaluate_stage_classifier --limit 50
    python manage.py evaluate_stage_classifier --input data/gemini_stage_test.jsonl
"""
import json
import os
from datetime import datetime, timezone

from django.conf import settings
from django.core.management.base import BaseCommand

from bonding.models import ConversationStageSnapshot
from bonding.services.conversation_analysis import (
    INTEREST_MAP,
    READINESS_THRESHOLD,
    detect_interests_from_text,
)
from bonding.services.gemini import analyze_conversation_stage

STAGE_LABELS = [choice[0] for choice in ConversationStageSnapshot.STAGE_CHOICES]
INTEREST_LABELS = list(INTEREST_MAP.keys())

DEFAULT_INPUT = os.path.join(settings.BASE_DIR, "data", "gemini_stage_test.jsonl")
DEFAULT_OUTPUT_DIR = os.path.join(settings.BASE_DIR, "data", "eval_results")


class Command(BaseCommand):
    help = "Compara a heurística por palavra-chave com o classificador Gemini de estágio/interesses"

    def add_arguments(self, parser):
        parser.add_argument("--input", default=DEFAULT_INPUT)
        parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Limita quantos exemplos são enviados ao Gemini (controla custo de API)",
        )

    def handle(self, *args, **options):
        input_path = options["input"]
        if not os.path.exists(input_path):
            self.stderr.write(self.style.ERROR(
                f"Arquivo não encontrado: {input_path}\n"
                "Execute 'python manage.py prepare_training_data --task stage' primeiro."
            ))
            return

        examples = self._load_examples(input_path, options["limit"])
        self.stdout.write(f"Exemplos carregados: {len(examples)}")
        if not examples:
            self.stderr.write(self.style.ERROR("Nenhum exemplo válido no arquivo de teste."))
            return

        rows = [self._evaluate_example(ex) for ex in examples]

        metrics = self._compute_metrics(rows)

        os.makedirs(options["output_dir"], exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = os.path.join(options["output_dir"], f"stage_eval_{timestamp}.json")
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(metrics, fh, ensure_ascii=False, indent=2)

        self._print_summary(metrics)
        self.stdout.write(self.style.SUCCESS(f"\nResultados salvos em: {out_path}"))

        self._maybe_plot_confusion_matrix(metrics, options["output_dir"], timestamp)

    # =========================================================

    def _load_examples(self, input_path: str, limit: int | None) -> list[dict]:
        examples = []
        with open(input_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                examples.append(json.loads(line))
        if limit:
            examples = examples[:limit]
        return examples

    def _parse_example(self, example: dict) -> tuple[list[dict], dict]:
        prompt_text = example["contents"][0]["parts"][0]["text"]
        ground_truth = json.loads(example["contents"][1]["parts"][0]["text"])

        chat_history = prompt_text.split("Mensagens:\n", 1)[1].rstrip("\n")
        messages = []
        for line in chat_history.split("\n"):
            if ": " not in line:
                continue
            label, content = line.split(": ", 1)
            messages.append({"label": label, "content": content})
        return messages, ground_truth

    def _evaluate_example(self, example: dict) -> dict:
        messages, ground_truth = self._parse_example(example)
        full_text = " ".join(m["content"] for m in messages)
        message_count = len(messages)

        heuristic_interests = detect_interests_from_text(full_text)
        heuristic_ready = message_count >= READINESS_THRESHOLD

        gemini_result = analyze_conversation_stage(messages)
        gemini_stage = gemini_result.get("stage", "quebra_gelo")
        gemini_ready = gemini_stage in ConversationStageSnapshot.READY_STAGES

        true_stage = ground_truth.get("stage", "quebra_gelo")
        true_ready = true_stage in ConversationStageSnapshot.READY_STAGES

        return {
            "true_stage": true_stage,
            "true_interests": ground_truth.get("interests", []),
            "true_ready": true_ready,
            "heuristic_interests": heuristic_interests,
            "heuristic_ready": heuristic_ready,
            "gemini_stage": gemini_stage,
            "gemini_interests": gemini_result.get("interests", []),
            "gemini_ready": gemini_ready,
        }

    # =========================================================

    def _compute_metrics(self, rows: list[dict]) -> dict:
        from sklearn.metrics import (
            accuracy_score,
            classification_report,
            confusion_matrix,
            f1_score,
        )
        from sklearn.preprocessing import MultiLabelBinarizer

        n = len(rows)

        # --- Estágio (só Gemini produz um estágio; heurística não tem essa granularidade) ---
        y_true_stage = [r["true_stage"] for r in rows]
        y_pred_stage = [r["gemini_stage"] for r in rows]
        stage_accuracy = accuracy_score(y_true_stage, y_pred_stage)
        stage_f1_macro = f1_score(y_true_stage, y_pred_stage, labels=STAGE_LABELS, average="macro", zero_division=0)
        stage_confusion = confusion_matrix(y_true_stage, y_pred_stage, labels=STAGE_LABELS).tolist()
        stage_report = classification_report(
            y_true_stage, y_pred_stage, labels=STAGE_LABELS, zero_division=0, output_dict=True,
        )

        # --- Interesses (multi-label) ---
        mlb = MultiLabelBinarizer(classes=INTEREST_LABELS)
        y_true_interests = mlb.fit_transform([r["true_interests"] for r in rows])
        y_pred_heuristic_interests = mlb.transform([r["heuristic_interests"] for r in rows])
        y_pred_gemini_interests = mlb.transform([r["gemini_interests"] for r in rows])

        heuristic_interest_report = classification_report(
            y_true_interests, y_pred_heuristic_interests,
            target_names=INTEREST_LABELS, zero_division=0, output_dict=True,
        )
        gemini_interest_report = classification_report(
            y_true_interests, y_pred_gemini_interests,
            target_names=INTEREST_LABELS, zero_division=0, output_dict=True,
        )

        # --- Prontidão binária: heurística (contagem de mensagens) vs. Gemini (estágio) ---
        y_true_ready = [r["true_ready"] for r in rows]
        heuristic_ready_accuracy = accuracy_score(y_true_ready, [r["heuristic_ready"] for r in rows])
        gemini_ready_accuracy = accuracy_score(y_true_ready, [r["gemini_ready"] for r in rows])

        return {
            "n_examples": n,
            "stage": {
                "labels": STAGE_LABELS,
                "accuracy": stage_accuracy,
                "f1_macro": stage_f1_macro,
                "confusion_matrix": stage_confusion,
                "classification_report": stage_report,
            },
            "interests": {
                "labels": INTEREST_LABELS,
                "heuristic": heuristic_interest_report,
                "gemini": gemini_interest_report,
            },
            "readiness": {
                "heuristic_accuracy": heuristic_ready_accuracy,
                "gemini_accuracy": gemini_ready_accuracy,
            },
        }

    def _print_summary(self, metrics: dict) -> None:
        self.stdout.write("\n=== Estágio da conversa (Gemini vs. ground truth) ===")
        self.stdout.write(f"Acurácia: {metrics['stage']['accuracy']:.3f}")
        self.stdout.write(f"F1 macro: {metrics['stage']['f1_macro']:.3f}")

        self.stdout.write("\n=== Prontidão para rolê (binário) ===")
        self.stdout.write(f"Heurística (contagem de mensagens): {metrics['readiness']['heuristic_accuracy']:.3f}")
        self.stdout.write(f"Gemini (estágio da conversa):        {metrics['readiness']['gemini_accuracy']:.3f}")

        self.stdout.write("\n=== Interesses (F1 macro multi-label) ===")
        heuristic_f1 = metrics["interests"]["heuristic"].get("macro avg", {}).get("f1-score", 0)
        gemini_f1 = metrics["interests"]["gemini"].get("macro avg", {}).get("f1-score", 0)
        self.stdout.write(f"Heurística (keywords): {heuristic_f1:.3f}")
        self.stdout.write(f"Gemini:                {gemini_f1:.3f}")

    def _maybe_plot_confusion_matrix(self, metrics: dict, output_dir: str, timestamp: str) -> None:
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            self.stdout.write(self.style.WARNING("matplotlib não instalado — pulando geração do gráfico."))
            return

        matrix = metrics["stage"]["confusion_matrix"]
        labels = metrics["stage"]["labels"]

        fig, ax = plt.subplots(figsize=(6, 5))
        im = ax.imshow(matrix, cmap="Blues")
        ax.set_xticks(range(len(labels)))
        ax.set_yticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_yticklabels(labels)
        ax.set_xlabel("Predito (Gemini)")
        ax.set_ylabel("Real (ground truth)")
        ax.set_title("Matriz de confusão — estágio da conversa")
        for i in range(len(labels)):
            for j in range(len(labels)):
                ax.text(j, i, matrix[i][j], ha="center", va="center", color="black")
        fig.colorbar(im)
        fig.tight_layout()

        out_path = os.path.join(output_dir, f"confusion_matrix_{timestamp}.png")
        fig.savefig(out_path)
        plt.close(fig)
        self.stdout.write(self.style.SUCCESS(f"Matriz de confusão salva em: {out_path}"))
