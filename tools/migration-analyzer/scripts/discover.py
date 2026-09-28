#!/usr/bin/env python3
"""
discover.py — Detecta qué sistema de catálogo/CPQ hay instalado en un org
Salesforce, como primer paso del Agente de Migración CPQ a Revenue Cloud.

Requiere: sf CLI instalado y con sesión iniciada contra el org objetivo.
    sf org login web --alias mi-org

Uso:
    python3 discover.py --alias mi-org
    python3 discover.py --alias mi-org --out ../output/mi-org.discovery.json

Qué hace:
    1. Confirma la conexión al org (sf org display).
    2. Lista todos los SObjects visibles (sf sobject list).
    3. Clasifica los objetos por prefijo/nombre conocido para detectar:
         - SBQQ            → Salesforce CPQ (paquete SBQQ)
         - INDUSTRIES_EPC   → Industries CPQ/EPC (paquete vlocity_cmt)
         - REVENUE_CLOUD    → objetos nativos de Revenue Cloud (RLM)
    4. Escribe un informe JSON con lo detectado, para usarlo como entrada
       del extractor correspondiente (extract_sbqq.py, etc.).

No escribe nada en el org: solo lecturas (org display, sobject list).
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone

# Prefijos / nombres de objeto que identifican cada sistema de origen.
# Se buscan como substring del API name completo (case-sensitive, como
# los devuelve Salesforce).
SIGNATURES = {
    "SBQQ": {
        "label": "Salesforce CPQ (SBQQ)",
        "prefixes": ["SBQQ__"],
    },
    "INDUSTRIES_EPC": {
        "label": "Industries CPQ / EPC (Vlocity)",
        "prefixes": ["vlocity_cmt__"],
    },
    "REVENUE_CLOUD": {
        "label": "Revenue Cloud (RLM) nativo",
        # Objetos nativos introducidos con Revenue Cloud / RLM que no
        # existen en orgs solo-CPQ clásico. Sin namespace porque son
        # estándar.
        "objects": [
            "ProductSellingModel",
            "ProductSellingModelOption",
            "PriceAdjustmentSchedule",
            "PriceAdjustmentTier",
            "AttributeDefinition",
            "AttributePicklist",
            "AttributeCategory",
            "ProductAttributeDefinition",
            "ProductComponentGroup",
            "ProductRelatedComponent",
            "ExpressionSetDefinition",
            "CostBook",
            "CostBookEntry",
        ],
    },
}


def run_sf(args, org_alias):
    """Ejecuta un comando sf CLI con --json y devuelve el dict resultado."""
    cmd = ["sf"] + args + ["--target-org", org_alias, "--json"]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
    except FileNotFoundError:
        sys.exit(
            "No se encontró el ejecutable 'sf'. Instala Salesforce CLI: "
            "https://developer.salesforce.com/tools/salesforcecli"
        )
    except subprocess.TimeoutExpired:
        sys.exit(f"Comando 'sf {' '.join(args)}' excedió el timeout.")

    stdout = result.stdout.strip()
    if not stdout:
        sys.exit(
            f"Comando 'sf {' '.join(args)}' no devolvió salida.\n"
            f"stderr: {result.stderr.strip()}"
        )
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        sys.exit(f"Salida no JSON de 'sf {' '.join(args)}':\n{stdout[:500]}")

    if payload.get("status") != 0:
        sys.exit(
            f"'sf {' '.join(args)}' falló: "
            f"{payload.get('message', 'sin detalle')}"
        )
    return payload.get("result")


def confirm_connection(org_alias):
    result = run_sf(["org", "display"], org_alias)
    return {
        "org_alias": org_alias,
        "username": result.get("username"),
        "instance_url": result.get("instanceUrl"),
        "org_id": result.get("id"),
        "is_sandbox": result.get("sandboxId") is not None
        or "sandbox" in (result.get("instanceUrl") or "").lower(),
    }


def list_sobjects(org_alias):
    """
    Devuelve la lista de API names de todos los SObjects visibles.
    sf sobject list --json devuelve result como lista de strings.
    """
    result = run_sf(["sobject", "list", "--sobject", "all"], org_alias)
    if isinstance(result, list):
        return result
    # Algunas versiones de sf CLI devuelven {"result": {"objects": [...]}}
    if isinstance(result, dict) and "objects" in result:
        return result["objects"]
    sys.exit("Formato inesperado de 'sf sobject list --json'.")


def classify(sobject_names):
    names_set = set(sobject_names)
    findings = {}

    for system_id, spec in SIGNATURES.items():
        matched = []

        for prefix in spec.get("prefixes", []):
            matched.extend(n for n in sobject_names if n.startswith(prefix))

        for obj in spec.get("objects", []):
            if obj in names_set:
                matched.append(obj)

        if matched:
            findings[system_id] = {
                "label": spec["label"],
                "object_count": len(matched),
                "sample_objects": sorted(matched)[:15],
            }

    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alias", required=True, help="Alias del org autenticado con sf CLI"
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Ruta del JSON de salida (por defecto: stdout)",
    )
    args = parser.parse_args()

    print(f"Conectando a org '{args.alias}'...", file=sys.stderr)
    connection = confirm_connection(args.alias)

    print("Listando SObjects visibles...", file=sys.stderr)
    sobjects = list_sobjects(args.alias)
    print(f"  {len(sobjects)} objetos encontrados.", file=sys.stderr)

    findings = classify(sobjects)

    if not findings:
        print(
            "AVISO: no se detectó SBQQ, Industries EPC ni objetos nativos "
            "de Revenue Cloud. Revisa manualmente los objetos del org.",
            file=sys.stderr,
        )

    report = {
        "meta": {
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "tool": "discover.py",
        },
        "connection": connection,
        "total_sobjects": len(sobjects),
        "detected_systems": findings,
        "next_step": _suggest_next_step(findings),
    }

    output = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        print(f"Informe escrito en {args.out}", file=sys.stderr)
    else:
        print(output)


def _suggest_next_step(findings):
    if "SBQQ" in findings and "INDUSTRIES_EPC" in findings:
        return (
            "Org con ambos orígenes (SBQQ + Industries EPC). Ejecutar "
            "extract_sbqq.py y el extractor de Industries por separado; "
            "revisar cuál es el catálogo activo antes de migrar."
        )
    if "SBQQ" in findings:
        return "Ejecutar scripts/extract_sbqq.py --alias <alias>"
    if "INDUSTRIES_EPC" in findings:
        return (
            "Origen Industries CPQ/EPC detectado. Extractor específico "
            "pendiente de implementar (ver README del tool)."
        )
    if "REVENUE_CLOUD" in findings:
        return (
            "El org ya tiene objetos nativos de Revenue Cloud. Confirmar "
            "si es el destino de la migración o si conviven ambos modelos."
        )
    return "Sin sistema detectado automáticamente. Inspeccionar manualmente."


if __name__ == "__main__":
    main()
