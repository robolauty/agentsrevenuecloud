#!/usr/bin/env python3
"""
generate_load.py — Genera ficheros de carga (SObject Tree + plan.json) para
Revenue Cloud a partir del canónico ya clasificado y revisado.

Usa el formato SObject Tree de Salesforce (records con 'attributes.type' y
'referenceId', resueltos por 'sf data import tree --plan plan.json'). Las
relaciones entre registros (producto -> categoría, precio -> producto,
etc.) se resuelven por referencia ("@refId"), sin necesidad de campos de
external id en el destino.

IMPORTANTE — no carga todo el canónico a ciegas:
  - Solo incluye elementos con migration.classification en
    {direct, transformable} Y migration.reviewed_by_human == true.
    Lo que no cumple eso se omite y queda listado en load_summary.md con
    el motivo — no se descarta en silencio.
  - Los componentes de bundle (ProductRelatedComponent) nunca se generan
    aquí: classify_gaps.py los marca siempre 'redesign', y ese rediseño
    (agrupamiento en ProductComponentGroup) es una decisión que toma el
    agente/humano, no este script.
  - ProductSellingModel se genera solo con --include-selling-models,
    porque su valor no viene de un dato real de SBQQ sino de una
    inferencia sobre selling_model del canónico — revisar antes de cargar
    (ver config/load_mapping.json).

Los nombres de objeto/campo salen de config/load_mapping.json, no están
hardcodeados aquí: los bloques marcados "verify": true en ese fichero
deben contrastarse contra el org destino antes de una carga real.

Uso:
    python3 generate_load.py \
        --canonical ../output/mi-org/canonical.classified.json \
        --mapping ../config/load_mapping.json \
        --out ../output/mi-org/load
"""

import argparse
import json
from pathlib import Path


def is_ready(entity):
    m = entity.get("migration", {})
    return m.get("classification") in ("direct", "transformable") and m.get(
        "reviewed_by_human"
    ) is True


def ref(prefix, key):
    safe = str(key).replace(" ", "_").replace(":", "_")
    return f"{prefix}_{safe}"


def tree(object_name, records):
    return {
        "records": [
            {"attributes": {"type": object_name, "referenceId": r.pop("_ref")}, **r}
            for r in records
        ]
    }


def build_categories(canonical, mapping, skipped):
    spec = mapping["category"]
    fields = spec["fields"]
    out = []
    refs = {}
    for cat in canonical.get("categories", []):
        if not is_ready(cat):
            skipped.append(_skip_entry("category", cat))
            continue
        r = ref("cat", cat["id"])
        refs[cat["id"]] = r
        record = {"_ref": r, fields["name"]: cat.get("name")}
        out.append(record)
    # Segunda pasada: resolver parent_id ahora que todos los refs existen.
    for cat in canonical.get("categories", []):
        if cat["id"] not in refs or not cat.get("parent_id"):
            continue
        parent_ref = refs.get(cat["parent_id"])
        if parent_ref:
            for record in out:
                if record["_ref"] == refs[cat["id"]]:
                    record[fields["parent_id"]] = f"@{parent_ref}"
    return out, refs, spec["object"]


def build_products(canonical, mapping, skipped):
    spec = mapping["product"]
    fields = spec["fields"]
    out = []
    refs = {}
    for p in canonical.get("products", []):
        if not is_ready(p):
            skipped.append(_skip_entry("product", p))
            continue
        r = ref("prod", p["id"])
        refs[p["id"]] = r
        record = {"_ref": r, fields["name"]: p.get("name")}
        if p.get("code"):
            record[fields["code"]] = p["code"]
        if p.get("description"):
            record[fields["description"]] = p["description"]
        if "active" in p:
            record[fields["active"]] = p.get("active", True)
        if p.get("family"):
            record[fields["family"]] = p["family"]
        out.append(record)
    return out, refs, spec["object"]


def build_category_assignments(canonical, mapping, category_refs, product_refs, skipped):
    spec = mapping["category_assignment"]
    fields = spec["fields"]
    out = []
    for p in canonical.get("products", []):
        if p["id"] not in product_refs:
            continue
        for cat_id in p.get("category_ids", []):
            cat_ref = category_refs.get(cat_id)
            if not cat_ref:
                skipped.append(
                    {
                        "kind": "category_assignment",
                        "id": f"{p['id']}::{cat_id}",
                        "reason": "Categoría referenciada no está lista/cargada.",
                    }
                )
                continue
            out.append(
                {
                    "_ref": ref("catprod", f"{p['id']}_{cat_id}"),
                    fields["product_ref"]: f"@{product_refs[p['id']]}",
                    fields["category_ref"]: f"@{cat_ref}",
                }
            )
    return out, spec["object"]


def build_pricebooks(canonical, mapping, skipped):
    spec = mapping["pricebook"]
    fields = spec["fields"]
    out = []
    refs = {}
    for pb in canonical.get("pricebooks", []):
        if not is_ready(pb):
            skipped.append(_skip_entry("pricebook", pb))
            continue
        r = ref("pb", pb["id"])
        refs[pb["id"]] = r
        record = {"_ref": r, fields["name"]: pb.get("name")}
        if "active" in pb:
            record[fields["active"]] = pb.get("active", True)
        out.append(record)
    return out, refs, spec["object"]


def build_prices(canonical, mapping, product_refs, pricebook_refs, skipped):
    spec = mapping["price"]
    fields = spec["fields"]
    out = []
    for price in canonical.get("prices", []):
        price_id = f"{price.get('product_id')}::{price.get('pricebook_id')}"
        if not is_ready(price):
            skipped.append(_skip_entry("price", price, entity_id=price_id))
            continue
        prod_ref = product_refs.get(price.get("product_id"))
        pb_ref = pricebook_refs.get(price.get("pricebook_id"))
        if not prod_ref or not pb_ref:
            skipped.append(
                {
                    "kind": "price",
                    "id": f"{price.get('product_id')}::{price.get('pricebook_id')}",
                    "reason": "Producto o pricebook referenciado no está listo/cargado.",
                }
            )
            continue
        record = {
            "_ref": ref("price", f"{price.get('product_id')}_{price.get('pricebook_id')}"),
            fields["product_ref"]: f"@{prod_ref}",
            fields["pricebook_ref"]: f"@{pb_ref}",
            fields["amount"]: price.get("amount"),
        }
        out.append(record)
    return out, spec["object"]


def build_selling_models(canonical, mapping, product_refs, skipped):
    """
    Solo se llama si --include-selling-models. selling_model del canónico
    es una inferencia (ver adapt_sbqq_to_canonical.py), no un dato migrado
    1:1 — por eso cada registro generado se lista igualmente en el
    resumen bajo "requiere validación manual", incluso si se genera.
    """
    spec = mapping["selling_model"]
    fields = spec["fields"]
    defaults = spec["default_values"]
    type_map = {
        "recurring": defaults["selling_model_type_if_recurring"],
        "one_time": defaults["selling_model_type_if_one_time"],
    }
    out = []
    needs_validation = []
    for p in canonical.get("products", []):
        if p["id"] not in product_refs:
            continue
        selling_model = p.get("selling_model", "unknown")
        model_type = type_map.get(selling_model)
        if not model_type:
            needs_validation.append(
                {
                    "kind": "selling_model",
                    "id": p["id"],
                    "reason": f"selling_model='{selling_model}' sin mapeo por "
                    "defecto (usage/term/unknown) — definir con el cliente.",
                }
            )
            continue
        r = ref("sm", p["id"])
        out.append(
            {
                "_ref": r,
                fields["name"]: f"{p.get('name')} - Selling Model",
                fields["selling_model_type"]: model_type,
            }
        )
        needs_validation.append(
            {
                "kind": "selling_model",
                "id": p["id"],
                "reason": f"Generado como '{model_type}' por inferencia desde "
                "SBQQ — confirmar con el cliente antes de cargar.",
            }
        )
    return out, spec["object"], needs_validation


def _skip_entry(kind, entity, entity_id=None):
    m = entity.get("migration", {})
    return {
        "kind": kind,
        "id": entity_id if entity_id is not None else entity.get("id", "sin id"),
        "reason": f"classification='{m.get('classification')}', "
        f"reviewed_by_human={m.get('reviewed_by_human')}",
    }


def write_tree_file(out_dir, filename, object_name, records):
    if not records:
        return None
    payload = tree(object_name, [dict(r) for r in records])
    path = out_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--include-selling-models",
        action="store_true",
        help="Generar ProductSellingModel (requiere validación manual siempre).",
    )
    args = parser.parse_args()

    with open(args.canonical, encoding="utf-8") as f:
        canonical = json.load(f)
    with open(args.mapping, encoding="utf-8") as f:
        mapping = json.load(f)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    skipped = []
    plan_entries = []

    categories, category_refs, cat_obj = build_categories(canonical, mapping, skipped)
    path = write_tree_file(out_dir, "01_ProductCategory.json", cat_obj, categories)
    if path:
        plan_entries.append({"sobject": cat_obj, "saveRefs": True, "resolveRefs": True, "files": [path.name]})

    products, product_refs, prod_obj = build_products(canonical, mapping, skipped)
    path = write_tree_file(out_dir, "02_Product2.json", prod_obj, products)
    if path:
        plan_entries.append({"sobject": prod_obj, "saveRefs": True, "resolveRefs": True, "files": [path.name]})

    cat_assign, cat_assign_obj = build_category_assignments(
        canonical, mapping, category_refs, product_refs, skipped
    )
    path = write_tree_file(out_dir, "03_ProductCategoryProduct.json", cat_assign_obj, cat_assign)
    if path:
        plan_entries.append({"sobject": cat_assign_obj, "saveRefs": False, "resolveRefs": True, "files": [path.name]})

    selling_model_validation = []
    if args.include_selling_models:
        selling_models, sm_obj, selling_model_validation = build_selling_models(
            canonical, mapping, product_refs, skipped
        )
        path = write_tree_file(out_dir, "04_ProductSellingModel.json", sm_obj, selling_models)
        if path:
            plan_entries.append({"sobject": sm_obj, "saveRefs": True, "resolveRefs": True, "files": [path.name]})

    pricebooks, pricebook_refs, pb_obj = build_pricebooks(canonical, mapping, skipped)
    path = write_tree_file(out_dir, "05_Pricebook2.json", pb_obj, pricebooks)
    if path:
        plan_entries.append({"sobject": pb_obj, "saveRefs": True, "resolveRefs": True, "files": [path.name]})

    prices, price_obj = build_prices(canonical, mapping, product_refs, pricebook_refs, skipped)
    path = write_tree_file(out_dir, "06_PricebookEntry.json", price_obj, prices)
    if path:
        plan_entries.append({"sobject": price_obj, "saveRefs": False, "resolveRefs": True, "files": [path.name]})

    plan_path = out_dir / "plan.json"
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump({"sobjects": plan_entries}, f, indent=2, ensure_ascii=False)

    _write_summary(
        out_dir / "load_summary.md",
        canonical,
        counts={
            "ProductCategory": len(categories),
            "Product2": len(products),
            "ProductCategoryProduct": len(cat_assign),
            "Pricebook2": len(pricebooks),
            "PricebookEntry": len(prices),
        },
        skipped=skipped,
        selling_model_validation=selling_model_validation,
    )

    print(f"Ficheros de carga en {out_dir}")
    print(f"  {len(plan_entries)} objetos con registros, plan.json listo.")
    print(f"  {len(skipped)} elementos omitidos (ver load_summary.md).")
    print(
        "\nEjecutar contra sandbox primero:\n"
        f"  sf data import tree --plan {plan_path} --target-org <alias>"
    )


def _write_summary(path, canonical, counts, skipped, selling_model_validation):
    org_alias = canonical.get("meta", {}).get("org_alias", "?")
    lines = [
        f"# Resumen de carga — {org_alias}",
        "",
        "## Registros generados",
        "",
        "| Objeto | Registros |",
        "|---|---|",
    ]
    for obj, n in counts.items():
        lines.append(f"| {obj} | {n} |")

    lines += [
        "",
        f"## Omitidos ({len(skipped)})",
        "",
        "No cumplían `classification in (direct, transformable)` y "
        "`reviewed_by_human == true`. Revisarlos antes de una nueva pasada, "
        "no ignorarlos.",
        "",
    ]
    if skipped:
        lines += ["| Tipo | Id | Motivo |", "|---|---|---|"]
        for s in skipped:
            lines.append(f"| {s['kind']} | {s['id']} | {s['reason']} |")
    else:
        lines.append("Ninguno.")

    if selling_model_validation:
        lines += [
            "",
            "## ProductSellingModel — requiere validación manual",
            "",
            "Generados por inferencia desde SBQQ, no desde un dato real. "
            "Confirmar con el cliente antes de cargar:",
            "",
            "| Producto | Nota |",
            "|---|---|",
        ]
        for v in selling_model_validation:
            lines.append(f"| {v['id']} | {v['reason']} |")

    lines += [
        "",
        "## Antes de ejecutar la carga",
        "",
        "1. Correr primero contra una sandbox, nunca directo a producción.",
        "2. Contrastar `config/load_mapping.json` contra "
        "`sf sobject describe` del org destino — los bloques marcados "
        "`\"verify\": true` no están confirmados.",
        "3. `sf data import tree --plan plan.json --target-org <sandbox>` "
        "inserta todo en una transacción por objeto; revisar el resultado "
        "antes de repetir en otro org.",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
