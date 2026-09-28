#!/usr/bin/env python3
"""
adapt_sbqq_to_canonical.py — Normaliza el volcado crudo de extract_sbqq.py
al modelo canónico (schema/canonical_catalog.schema.json).

Solo hace mapeo determinista (1:1 o de transformación mecánica simple).
Lo ambiguo (price rules en Apex, reglas de configuración complejas,
atributos que en realidad son variantes) se deja fuera de este script:
va al informe de gaps con ayuda de un LLM, en una segunda pasada.

Uso:
    python3 adapt_sbqq_to_canonical.py \
        --raw ../output/mi-org/raw \
        --out ../output/mi-org/canonical.json \
        --org-alias mi-org
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load(raw_dir, object_name):
    path = Path(raw_dir) / f"{object_name}.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def source_ref(system, obj, record):
    return {
        "system": system,
        "object": obj,
        "record_id": record.get("Id"),
        "raw": record,
    }


def pending_migration(notes=None):
    return {"classification": "pending", "notes": notes or ""}


def adapt_products(raw_dir):
    products = []
    for rec in load(raw_dir, "Product2"):
        is_bundle = bool(rec.get("SBQQ__ProductType__c") == "Bundle") or bool(
            rec.get("SBQQ__ConfigurationType__c") == "Allowed"
        )
        products.append(
            {
                "id": rec["Id"],
                "name": rec.get("Name"),
                "code": rec.get("ProductCode"),
                "description": rec.get("Description"),
                "type": "bundle" if is_bundle else "simple",
                "active": rec.get("IsActive", True),
                "family": rec.get("Family"),
                "category_ids": [],
                "attributes": [],
                "components": [],
                "selling_model": "unknown",
                "custom_fields": {
                    k: v
                    for k, v in rec.items()
                    if k.endswith("__c")
                    and k
                    not in (
                        "SBQQ__ProductType__c",
                        "SBQQ__ConfigurationType__c",
                    )
                },
                "source": source_ref("SBQQ", "Product2", rec),
                "migration": pending_migration(
                    "Clasificar selling_model (SBQQ__SubscriptionType__c / "
                    "SBQQ__SubscriptionPricing__c) y revisar bundle vs simple."
                ),
            }
        )
    return products


def adapt_categories(raw_dir):
    categories = []
    for rec in load(raw_dir, "ProductCategory"):
        categories.append(
            {
                "id": rec["Id"],
                "name": rec.get("Name"),
                "parent_id": rec.get("ParentCategoryId"),
                "catalog_id": rec.get("CatalogId"),
                "source": source_ref("SBQQ", "ProductCategory", rec),
                "migration": pending_migration(),
            }
        )
    return categories


def adapt_pricebooks(raw_dir):
    pricebooks = []
    for rec in load(raw_dir, "Pricebook2"):
        pricebooks.append(
            {
                "id": rec["Id"],
                "name": rec.get("Name"),
                "active": rec.get("IsActive", True),
                "is_standard": rec.get("IsStandard", False),
                "currency": rec.get("CurrencyIsoCode"),
                "source": source_ref("SBQQ", "Pricebook2", rec),
                "migration": pending_migration(),
            }
        )
    return pricebooks


def adapt_prices(raw_dir):
    prices = []
    for rec in load(raw_dir, "PricebookEntry"):
        prices.append(
            {
                "product_id": rec.get("Product2Id"),
                "pricebook_id": rec.get("Pricebook2Id"),
                "amount": rec.get("UnitPrice"),
                "currency": rec.get("CurrencyIsoCode"),
                "charge_type": "unknown",
                "tiers": [],
                "source": source_ref("SBQQ", "PricebookEntry", rec),
                "migration": pending_migration(
                    "Determinar charge_type real: revisar "
                    "SBQQ__PricingMethod__c / SBQQ__ChargeType__c en Product2."
                ),
            }
        )
    return prices


def adapt_components(raw_dir):
    """
    SBQQ__ProductOption__c es la relación bundle -> hijo. Se agrupa por
    ConfiguredSKU (producto padre) y se agrega como 'components' dentro del
    producto correspondiente por el script de merge, no aquí: aquí se deja
    como lista plana para no perder ningún registro origen.
    """
    components = []
    for rec in load(raw_dir, "SBQQ__ProductOption__c"):
        components.append(
            {
                "parent_product_id": rec.get("SBQQ__ConfiguredSKU__c"),
                "child_product_id": rec.get("SBQQ__OptionalSKU__c"),
                "group": rec.get("SBQQ__Feature__c"),
                "min_quantity": rec.get("SBQQ__MinOptionQuantity__c"),
                "max_quantity": rec.get("SBQQ__MaxOptionQuantity__c"),
                "default_quantity": rec.get("SBQQ__Quantity__c"),
                "required": rec.get("SBQQ__Required__c", False),
                "selected_by_default": rec.get("SBQQ__SelectedByDefault__c", False),
                "source": source_ref("SBQQ", "SBQQ__ProductOption__c", rec),
                "migration": pending_migration(),
            }
        )
    return components


def merge_components_into_products(products, components):
    by_parent = {}
    for c in components:
        by_parent.setdefault(c["parent_product_id"], []).append(c)

    for p in products:
        matched = by_parent.get(p["id"], [])
        p["components"] = [
            {k: v for k, v in c.items() if k != "parent_product_id"}
            for c in matched
        ]
    return products


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, help="Directorio de extract_sbqq.py")
    parser.add_argument("--out", required=True, help="Ruta del JSON canónico de salida")
    parser.add_argument("--org-alias", default=None)
    args = parser.parse_args()

    products = adapt_products(args.raw)
    categories = adapt_categories(args.raw)
    pricebooks = adapt_pricebooks(args.raw)
    prices = adapt_prices(args.raw)
    components = adapt_components(args.raw)
    products = merge_components_into_products(products, components)

    canonical = {
        "meta": {
            "schema_version": "0.1.0",
            "source_system": "SBQQ",
            "org_alias": args.org_alias,
            "extracted_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        },
        "categories": categories,
        "attributes": [],  # TODO: SBQQ__ConfigurationAttribute__c -> attribute[]
        "products": products,
        "pricebooks": pricebooks,
        "prices": prices,
        "rules": [],  # TODO: SBQQ__PriceRule__c, SBQQ__ProductRule__c
        "promotions": [],
        "unmapped": [],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(canonical, f, indent=2, ensure_ascii=False)

    print(
        f"Canónico escrito en {out_path}: "
        f"{len(products)} productos, {len(categories)} categorías, "
        f"{len(pricebooks)} pricebooks, {len(prices)} precios."
    )


if __name__ == "__main__":
    main()
