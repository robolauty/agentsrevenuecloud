#!/usr/bin/env python3
"""
classify_gaps.py — Aplica reglas deterministas de docs/mapping-sbqq-rlm.md
al modelo canónico para producir una primera clasificación
direct/transformable/redesign/review, y separa lo ambiguo en una cola de
revisión.

Esto NO reemplaza el análisis del agente 'revenue-cloud-cpq-migration':
resuelve automáticamente lo que tiene regla clara, y deja explícitamente
marcado lo que necesita criterio (revisar review_queue.json con el agente
o con un humano) en vez de adivinar.

Uso:
    python3 classify_gaps.py \
        --canonical ../output/mi-org/canonical.json \
        --out ../output/mi-org/canonical.classified.json \
        --review-out ../output/mi-org/review_queue.json \
        --report-out ../output/mi-org/gap_report.md
"""

import argparse
import json
from collections import Counter
from pathlib import Path


def classify_product(product):
    if product["type"] == "bundle":
        return (
            "transformable",
            "medium",
            "Bundle SBQQ: requiere rediseñar el agrupamiento como "
            "ProductComponentGroup / ProductRelatedComponent en vez de "
            "copiar SBQQ__ProductFeature__c 1:1.",
        )
    if product["type"] == "simple":
        return (
            "transformable",
            "low",
            "Producto simple: migra a Product2 pero requiere crear un "
            "ProductSellingModel explícito (no existe como tal en CPQ).",
        )
    return (
        "review",
        "unknown",
        f"type='{product['type']}' sin regla definida en "
        "docs/mapping-sbqq-rlm.md.",
    )


def classify_category(_category):
    return ("direct", "low", "Jerarquía de ProductCategory compatible.")


def classify_pricebook(_pricebook):
    return (
        "direct",
        "low",
        "Pricebook2 se mantiene. CostBook es nuevo, se configura aparte.",
    )


def classify_price(price):
    if price.get("charge_type") in (None, "unknown"):
        return (
            "review",
            "unknown",
            "charge_type sin determinar: revisar SBQQ__ChargeType__c / "
            "SBQQ__PricingMethod__c en el producto padre antes de decidir "
            "si migra como precio simple o con PriceAdjustmentSchedule.",
        )
    if price.get("tiers"):
        return (
            "transformable",
            "medium",
            "Tiene tramos de precio: requiere PriceAdjustmentSchedule / "
            "PriceAdjustmentTier en destino.",
        )
    return ("transformable", "low", "Precio base migra a PricebookEntry.")


def classify_component(_component):
    return (
        "redesign",
        "high",
        "SBQQ__ProductOption__c no mapea campo a campo a "
        "ProductRelatedComponent: requiere decisión de diseño sobre cómo "
        "agrupar los componentes en Revenue Cloud.",
    )


def apply_classification(entity, result, entity_kind, entity_id):
    classification, effort, note = result
    entity["migration"] = {
        "classification": classification,
        "effort": effort,
        "notes": note,
        "reviewed_by_human": False,
    }
    needs_review = classification == "review"
    return needs_review, {
        "kind": entity_kind,
        "id": entity_id,
        "classification": classification,
        "notes": note,
        "record": entity,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--review-out", required=True)
    parser.add_argument("--report-out", required=True)
    args = parser.parse_args()

    with open(args.canonical, encoding="utf-8") as f:
        canonical = json.load(f)

    review_queue = []
    counts = Counter()

    for p in canonical.get("products", []):
        needs_review, entry = apply_classification(
            p, classify_product(p), "product", p["id"]
        )
        counts[p["migration"]["classification"]] += 1
        if needs_review:
            review_queue.append(entry)

        for c in p.get("components", []):
            needs_review, entry = apply_classification(
                c,
                classify_component(c),
                "component",
                f"{p['id']}::{c.get('child_product_id')}",
            )
            counts[c["migration"]["classification"]] += 1
            if needs_review:
                review_queue.append(entry)

    for cat in canonical.get("categories", []):
        needs_review, entry = apply_classification(
            cat, classify_category(cat), "category", cat["id"]
        )
        counts[cat["migration"]["classification"]] += 1
        if needs_review:
            review_queue.append(entry)

    for pb in canonical.get("pricebooks", []):
        needs_review, entry = apply_classification(
            pb, classify_pricebook(pb), "pricebook", pb["id"]
        )
        counts[pb["migration"]["classification"]] += 1
        if needs_review:
            review_queue.append(entry)

    for price in canonical.get("prices", []):
        price_id = f"{price.get('product_id')}::{price.get('pricebook_id')}"
        needs_review, entry = apply_classification(
            price, classify_price(price), "price", price_id
        )
        counts[price["migration"]["classification"]] += 1
        if needs_review:
            review_queue.append(entry)

    # rules, promotions, unmapped: todavía no hay extractor que los llene
    # (ver README). Si en el futuro traen datos, van directos a review:
    # no hay regla determinista posible para SBQQ__PriceRule__c con
    # lógica arbitraria sin mirar el registro.
    for kind in ("rules", "promotions", "unmapped"):
        for item in canonical.get(kind, []):
            item.setdefault(
                "migration",
                {
                    "classification": "review",
                    "effort": "unknown",
                    "notes": f"'{kind}' requiere revisión manual siempre: "
                    "no hay regla determinista segura para lógica de "
                    "reglas/promociones.",
                    "reviewed_by_human": False,
                },
            )
            counts["review"] += 1
            review_queue.append(
                {
                    "kind": kind[:-1],
                    "id": item.get("id", "sin id"),
                    "classification": "review",
                    "notes": item["migration"]["notes"],
                    "record": item,
                }
            )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(canonical, f, indent=2, ensure_ascii=False)

    review_path = Path(args.review_out)
    with open(review_path, "w", encoding="utf-8") as f:
        json.dump(review_queue, f, indent=2, ensure_ascii=False)

    report_path = Path(args.report_out)
    _write_report(report_path, counts, review_queue, canonical)

    total = sum(counts.values())
    print(
        f"Clasificados {total} elementos: "
        + ", ".join(f"{k}={v}" for k, v in counts.items())
    )
    print(f"  {len(review_queue)} en cola de revisión -> {review_path}")
    print(f"  Canónico clasificado -> {out_path}")
    print(f"  Informe -> {report_path}")


def _write_report(path, counts, review_queue, canonical):
    org_alias = canonical.get("meta", {}).get("org_alias", "?")
    lines = [
        f"# Informe de gaps — {org_alias}",
        "",
        f"Generado por `classify_gaps.py` a partir del modelo canónico "
        f"({canonical.get('meta', {}).get('source_system', '?')}).",
        "",
        "## Resumen",
        "",
        "| Clasificación | Elementos |",
        "|---|---|",
    ]
    for classification in ("direct", "transformable", "redesign", "review"):
        lines.append(f"| {classification} | {counts.get(classification, 0)} |")

    lines += [
        "",
        f"**{len(review_queue)} elementos requieren revisión** antes de "
        "poder cerrar el manifiesto de migración (ver "
        "`review_queue.json`). No se han decidido automáticamente: cada "
        "uno necesita mirar el registro origen o consultar al cliente.",
        "",
        "## Cómo continuar",
        "",
        "1. Revisar `review_queue.json` con el agente "
        "`revenue-cloud-cpq-migration` (o manualmente) y resolver cada "
        "elemento a direct/transformable/redesign con su justificación.",
        "2. Los `redesign` necesitan una decisión de diseño explícita, "
        "no una transformación automática — documentarla en el "
        "manifiesto de migración.",
        "3. Con todo clasificado, generar la matriz de transformación y "
        "el plan de datos maestros/transaccionales/históricos que pide "
        "`agents/revenue-cloud-cpq-migration.md`.",
        "",
        "Este informe es un punto de partida, no el manifiesto final: "
        "no asume equivalencias 1:1 fuera de lo que "
        "`docs/mapping-sbqq-rlm.md` documenta explícitamente.",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
