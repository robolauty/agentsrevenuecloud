#!/usr/bin/env python3
"""
extract_sbqq.py — Extrae el catálogo Salesforce CPQ (paquete SBQQ) de un org
a ficheros JSON crudos, uno por objeto, para su posterior normalización al
modelo canónico (ver adapt_sbqq_to_canonical.py).

Requiere: sf CLI con sesión iniciada contra el org objetivo.

Uso:
    python3 extract_sbqq.py --alias mi-org --out ../output/mi-org/raw

Diseño:
    - Los campos a consultar por objeto se obtienen con 'sf sobject describe',
      no de una lista fija, para tolerar campos custom del cliente.
    - Se excluyen campos claramente irrelevantes (metadatos de sistema,
      campos de fórmula muy pesados) mediante una lista de exclusión.
    - Se usa Bulk API (sf data query --bulk) para objetos que puedan tener
      volumen alto (PricebookEntry, ProductOption); el resto usa REST.
    - Cada extracción se guarda como <output>/<ObjectName>.json, una lista
      de registros con TODOS los campos consultados.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Objetos SBQQ mínimos para un primer análisis de catálogo, precios y
# bundles. Se puede ampliar (SBQQ__PriceRule__c, SBQQ__DiscountSchedule__c,
# SBQQ__ProductRule__c...) en una segunda pasada, una vez validado el flujo.
OBJECTS = [
    {"name": "Product2", "bulk": False},
    {"name": "ProductCategory", "bulk": False},
    {"name": "Pricebook2", "bulk": False},
    {"name": "PricebookEntry", "bulk": True},
    {"name": "SBQQ__ProductOption__c", "bulk": True},
    {"name": "SBQQ__ProductFeature__c", "bulk": False},
    {"name": "SBQQ__ConfigurationAttribute__c", "bulk": False},
]

# Campos a excluir siempre, aunque existan en el describe: metadatos de
# sistema que no aportan al modelo canónico y encarecen la extracción.
FIELD_EXCLUDE_SUFFIXES = (
    "__History",
    "__Feed",
    "__Share",
)
FIELD_EXCLUDE_NAMES = {
    "SystemModstamp",
    "LastViewedDate",
    "LastReferencedDate",
    "IsDeleted",
}


def run_sf_json(args, timeout=300):
    try:
        result = subprocess.run(
            ["sf"] + args + ["--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        sys.exit("No se encontró 'sf'. Instala Salesforce CLI.")
    except subprocess.TimeoutExpired:
        sys.exit(f"Timeout en: sf {' '.join(args)}")

    stdout = result.stdout.strip()
    if not stdout:
        sys.exit(f"Sin salida en: sf {' '.join(args)}\n{result.stderr}")
    payload = json.loads(stdout)
    if payload.get("status") != 0:
        sys.exit(f"Error en 'sf {' '.join(args)}': {payload.get('message')}")
    return payload.get("result")


def describe_fields(object_name, org_alias):
    """Devuelve la lista de API names de campos consultables del objeto."""
    result = run_sf_json(
        ["sobject", "describe", "--sobject", object_name, "--target-org", org_alias]
    )
    fields = []
    for f in result.get("fields", []):
        name = f["name"]
        if name in FIELD_EXCLUDE_NAMES:
            continue
        if any(name.endswith(suf) for suf in FIELD_EXCLUDE_SUFFIXES):
            continue
        fields.append(name)
    return fields


def query_all(object_name, fields, org_alias, use_bulk):
    soql = f"SELECT {', '.join(fields)} FROM {object_name}"
    args = ["data", "query", "--query", soql, "--target-org", org_alias]
    if use_bulk:
        args += ["--bulk", "--wait", "30"]
    else:
        args += ["--result-format", "json"]
    result = run_sf_json(args, timeout=900 if use_bulk else 300)
    # 'sf data query' con --json devuelve {"records": [...], "totalSize": N}
    return result.get("records", [])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alias", required=True)
    parser.add_argument(
        "--out",
        required=True,
        help="Directorio donde escribir <Objeto>.json por cada objeto",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Limitar la extracción a estos API names de objeto",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    objects = OBJECTS
    if args.only:
        objects = [o for o in OBJECTS if o["name"] in args.only]
        if not objects:
            sys.exit(f"Ninguno de {args.only} está en la lista OBJECTS.")

    summary = {}
    for obj in objects:
        name = obj["name"]
        print(f"[{name}] describe...", file=sys.stderr)
        try:
            fields = describe_fields(name, args.alias)
        except SystemExit as e:
            print(f"[{name}] SALTADO: {e}", file=sys.stderr)
            summary[name] = {"status": "skipped", "reason": str(e)}
            continue

        print(f"[{name}] consultando {len(fields)} campos...", file=sys.stderr)
        records = query_all(name, fields, args.alias, obj["bulk"])

        out_file = out_dir / f"{name}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

        print(f"[{name}] {len(records)} registros -> {out_file}", file=sys.stderr)
        summary[name] = {"status": "ok", "count": len(records), "file": str(out_file)}

    summary_file = out_dir / "_extraction_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nResumen: {summary_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
