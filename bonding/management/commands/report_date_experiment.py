"""Prints (and optionally exports) the metrics promised in the TCC defense
answers, computed from real DateSuggestionFeedback rows:

- Spearman correlation between deterministic rank and LLM rank, within
  rounds that went through the semantic rerank ("Objetivo" answer).
- Real usage rate segmented by ranking_source (llm vs deterministic_fallback)
  ("Objetivo" answer's central metric).
- Invalid-index discard rate, and confirmation that no persisted row ever
  has an out-of-range index — makes the "mantida em zero por construção"
  claim measurable instead of assumed.
- Per-variant violation rate for the 4-variant experiment dataset ("Hipótese"
  answer) — expected ~0% for the 3 geographically grounded variants (radius
  check against the real UserLocationPing), and used to show the ai_pure
  baseline's hallucination rate (its suggested venue name doesn't match any
  real Overpass candidate fetched for that conversation).
"""
import json
from collections import defaultdict
from statistics import mean, median

from django.core.management.base import BaseCommand

from bonding.models import DateSuggestionFeedback
from bonding.services.external_integrations import estimate_distance_km
from bonding.services.date_experiment_variants import ALL_VARIANTS

try:
    from scipy.stats import spearmanr
except ImportError:  # pragma: no cover
    spearmanr = None


class Command(BaseCommand):
    help = "Calcula e imprime as metricas do experimento de recomendacao de dates (TCC)."

    def add_arguments(self, parser):
        parser.add_argument("--experiment-run-id", default=None)
        parser.add_argument("--output", default=None, help="Caminho de arquivo para gravar o relatorio em JSON.")

    def handle(self, *args, **options):
        report = {}

        report["spearman"] = self._spearman_report()
        report["usage_rate_by_ranking_source"] = self._usage_rate_report()
        report["invalid_index_discard_rate"] = self._invalid_index_report()

        run_id = options["experiment_run_id"] or self._latest_run_id()
        if run_id:
            report["experiment_run_id"] = run_id
            report["variant_violation_rate"] = self._variant_violation_report(run_id)
        else:
            self.stdout.write(self.style.WARNING("Nenhum experiment_run_id encontrado — pulando metricas de variante."))

        self._print(report)

        if options["output"]:
            with open(options["output"], "w", encoding="utf-8") as fh:
                json.dump(report, fh, ensure_ascii=False, indent=2)
            self.stdout.write(f"Relatorio gravado em {options['output']}")

    # ------------------------------------------------------------------
    # Metric 1: Spearman correlation (deterministic rank vs llm_rank)
    # ------------------------------------------------------------------
    def _spearman_report(self):
        if spearmanr is None:
            return {"error": "scipy nao disponivel"}

        rounds = defaultdict(list)
        rows = DateSuggestionFeedback.objects.filter(
            metadata__ranking_source="llm", llm_rank__isnull=False,
        ).values("round_id", "deterministic_score", "llm_rank")
        for row in rows:
            rounds[row["round_id"]].append(row)

        per_round_rho = []
        pooled_det, pooled_llm = [], []
        for round_id, entries in rounds.items():
            if len(entries) < 2:
                continue
            ordered_by_det = sorted(entries, key=lambda e: e["deterministic_score"] or 0, reverse=True)
            det_ranks = {id(e): rank for rank, e in enumerate(ordered_by_det, start=1)}
            det_rank_values = [det_ranks[id(e)] for e in entries]
            llm_rank_values = [e["llm_rank"] for e in entries]
            rho, _p = spearmanr(det_rank_values, llm_rank_values)
            per_round_rho.append(rho)
            pooled_det.extend(det_rank_values)
            pooled_llm.extend(llm_rank_values)

        result = {"rounds_included": len(per_round_rho)}
        if per_round_rho:
            result["mean_rho"] = round(mean(per_round_rho), 4)
            result["median_rho"] = round(median(per_round_rho), 4)
        if pooled_det:
            pooled_rho, _p = spearmanr(pooled_det, pooled_llm)
            result["pooled_rho"] = round(pooled_rho, 4)
        return result

    # ------------------------------------------------------------------
    # Metric 2: real usage rate segmented by ranking_source
    # ------------------------------------------------------------------
    def _usage_rate_report(self):
        totals = defaultdict(lambda: {"total": 0, "used": 0})
        rows = DateSuggestionFeedback.objects.values("metadata", "used_at")
        for row in rows:
            source = (row["metadata"] or {}).get("ranking_source") or "unknown"
            totals[source]["total"] += 1
            if row["used_at"] is not None:
                totals[source]["used"] += 1

        result = {}
        for source, counts in totals.items():
            rate = counts["used"] / counts["total"] if counts["total"] else 0.0
            result[source] = {**counts, "usage_rate": round(rate, 4)}
        return result

    # ------------------------------------------------------------------
    # Metric 3: invalid-index discard rate
    # ------------------------------------------------------------------
    def _invalid_index_report(self):
        rounds = defaultdict(lambda: {"rows": 0, "invalid_index_count": None})
        rows = DateSuggestionFeedback.objects.exclude(metadata__invalid_index_count__isnull=True).values(
            "round_id", "metadata",
        )
        for row in rows:
            count = (row["metadata"] or {}).get("invalid_index_count")
            entry = rounds[row["round_id"]]
            entry["rows"] += 1
            entry["invalid_index_count"] = count

        rounds_with_discards = [r for r in rounds.values() if (r["invalid_index_count"] or 0) > 0]
        rates = [
            r["invalid_index_count"] / (r["invalid_index_count"] + r["rows"])
            for r in rounds_with_discards
        ]
        out_of_range_persisted = DateSuggestionFeedback.objects.filter(
            metadata__ranking_source="llm",
        ).exclude(llm_rank__gte=1).count()

        return {
            "rounds_with_at_least_one_discard": len(rounds_with_discards),
            "mean_discard_rate_among_those_rounds": round(mean(rates), 4) if rates else 0.0,
            "persisted_rows_with_invalid_llm_rank": out_of_range_persisted,
        }

    # ------------------------------------------------------------------
    # Metric 4: per-variant radius/city violation rate
    # ------------------------------------------------------------------
    def _latest_run_id(self):
        row = (
            DateSuggestionFeedback.objects.exclude(experiment_run_id__isnull=True)
            .order_by("-created_at")
            .values_list("experiment_run_id", flat=True)
            .first()
        )
        return row

    def _variant_violation_report(self, run_id):
        result = {}
        for variant in ALL_VARIANTS:
            rows = list(
                DateSuggestionFeedback.objects.filter(
                    experiment_run_id=run_id, variant=variant,
                ).select_related("conversation")
            )
            total = len(rows)
            violations = 0
            for row in rows:
                if variant == "ai_pure":
                    # ai_pure has no OSM grounding at all — a violation here
                    # means the LLM named an establishment that doesn't
                    # match any real Overpass candidate fetched for this
                    # conversation, i.e. a plausible-sounding invented venue.
                    suggested_name = (row.place_name or "").strip().lower()
                    known_names = {
                        (name or "").strip().lower()
                        for name in (row.metadata or {}).get("known_candidate_names") or []
                    }
                    if not suggested_name or suggested_name not in known_names:
                        violations += 1
                    continue

                if row.place_latitude is None or row.place_longitude is None:
                    continue
                radius_km = (row.metadata or {}).get("radius_km") or 100
                ping = (
                    row.conversation.user1.location_pings.order_by("-created_at").first()
                    or row.conversation.user2.location_pings.order_by("-created_at").first()
                )
                if not ping:
                    continue
                distance = estimate_distance_km(
                    (ping.latitude, ping.longitude), (row.place_latitude, row.place_longitude),
                )
                if distance > radius_km:
                    violations += 1

            rate = violations / total if total else 0.0
            result[variant] = {"total": total, "violations": violations, "violation_rate": round(rate, 4)}
        return result

    # ------------------------------------------------------------------
    def _print(self, report):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== Correlacao de Spearman (rank determinístico vs llm_rank) ==="))
        self.stdout.write(json.dumps(report["spearman"], ensure_ascii=False, indent=2))

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== Taxa de uso real por origem (ranking_source) ==="))
        self.stdout.write(json.dumps(report["usage_rate_by_ranking_source"], ensure_ascii=False, indent=2))

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=== Taxa de descarte de indices invalidos ==="))
        self.stdout.write(json.dumps(report["invalid_index_discard_rate"], ensure_ascii=False, indent=2))

        if "variant_violation_rate" in report:
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING(
                f"=== Taxa de violacao de raio/cidade por variante (run {report['experiment_run_id']}) ==="
            ))
            self.stdout.write(json.dumps(report["variant_violation_rate"], ensure_ascii=False, indent=2))
