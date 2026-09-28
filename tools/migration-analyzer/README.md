# Migration Analyzer

Herramienta técnica del **Agente de Migración CPQ a Revenue Cloud**
(`agents/revenue-cloud-cpq-migration.md`). El agente define *qué* debe
producir un análisis de migración; esta herramienta es *cómo* se obtiene
ese análisis a partir de un org real, en vez de que el LLM lo infiera sin
datos.

## Flujo

```text
sf org login web --alias <org>
        ↓
discover.py            → detecta SBQQ / Industries EPC / Revenue Cloud nativo
        ↓
extract_sbqq.py         → vuelca el catálogo SBQQ a JSON crudo (1 fichero/objeto)
        ↓
adapt_sbqq_to_canonical.py → normaliza al modelo canónico (schema/)
        ↓
classify_gaps.py        → clasifica direct/transformable/redesign; deja lo ambiguo en review_queue.json
        ↓
agente revenue-cloud-cpq-migration → resuelve review_queue.json y cierra el manifiesto
        ↓
[pendiente] generador de carga hacia Revenue Cloud
```

Todo lo que toca el org es **solo lectura**. Nada de esto escribe en
Salesforce.

## Requisitos

- [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli) (`sf`) instalado.
- Python 3.9+, sin dependencias externas (usa solo `subprocess`/`json` de la
  librería estándar).
- Un usuario con permisos de **solo lectura** sobre los objetos de catálogo.
  Recomendado: permission set dedicado, no el usuario de admin.

## Uso

```bash
# 1. Conectar (una vez por org)
sf org login web --alias cliente-sandbox

# 2. Descubrir qué sistema de catálogo hay instalado
python3 scripts/discover.py --alias cliente-sandbox --out output/cliente-sandbox/discovery.json

# 3. Extraer el catálogo (solo si discover.py detectó SBQQ)
python3 scripts/extract_sbqq.py --alias cliente-sandbox --out output/cliente-sandbox/raw

# 4. Normalizar al modelo canónico
python3 scripts/adapt_sbqq_to_canonical.py \
    --raw output/cliente-sandbox/raw \
    --out output/cliente-sandbox/canonical.json \
    --org-alias cliente-sandbox

# 5. Clasificar direct/transformable/redesign con reglas deterministas
python3 scripts/classify_gaps.py \
    --canonical output/cliente-sandbox/canonical.json \
    --out output/cliente-sandbox/canonical.classified.json \
    --review-out output/cliente-sandbox/review_queue.json \
    --report-out output/cliente-sandbox/gap_report.md
```

El resultado (`canonical.json`) sigue `schema/canonical_catalog.schema.json`.
`classify_gaps.py` lo recorre aplicando las reglas de
`docs/mapping-sbqq-rlm.md` y produce tres salidas:

- `canonical.classified.json` — el mismo canónico, con `migration` relleno
  en cada entidad.
- `review_queue.json` — lo que no se pudo clasificar con una regla fija
  (precios sin `charge_type` determinado, price/product rules, cualquier
  cosa en `unmapped`). Cada entrada trae el registro completo para que se
  pueda revisar sin volver a mirar el crudo.
- `gap_report.md` — resumen en Markdown con el conteo por clasificación y
  los próximos pasos.

`review_queue.json` es la entrada del **agente `revenue-cloud-cpq-migration`**
(disponible como subagente en Claude Code sobre este repo): revisa cada
elemento con criterio, resuelve la clasificación con su justificación y
construye la matriz de transformación y el manifiesto que pide
`agents/revenue-cloud-cpq-migration.md`. El script no reemplaza ese
análisis — reduce el volumen a lo que de verdad requiere juicio.

`output/` está en `.gitignore` — el catálogo de un cliente no se commitea.

## Qué mapea cada script (y qué no)

**`discover.py`**
- Lee `sf org display` y `sf sobject list`.
- Clasifica por prefijo de namespace (`SBQQ__`, `vlocity_cmt__`) y por
  nombres de objetos nativos de Revenue Cloud.
- No lee datos de negocio, solo metadatos de objetos.

**`extract_sbqq.py`**
- Extrae `Product2`, `ProductCategory`, `Pricebook2`, `PricebookEntry`,
  `SBQQ__ProductOption__c`, `SBQQ__ProductFeature__c`,
  `SBQQ__ConfigurationAttribute__c`.
- Los campos por objeto salen del `describe`, no de una lista fija, así que
  incluye automáticamente los campos custom del cliente.
- **No incluye todavía**: `SBQQ__PriceRule__c`, `SBQQ__DiscountSchedule__c`,
  `SBQQ__ProductRule__c`, históricos de `Quote`/`Order`/`Contract`/`Asset`.
  Se añaden ampliando la lista `OBJECTS` cuando el flujo básico esté
  validado.

**`adapt_sbqq_to_canonical.py`**
- Mapea 1:1 lo simple: producto, categoría, pricebook, precio, y la
  relación bundle→componente de `SBQQ__ProductOption__c`.
- Marca todo con `migration.classification = "pending"` — este script no
  decide qué es `direct`/`transformable`/`redesign`, solo normaliza. Esa
  clasificación es el siguiente paso (análisis de gaps).
- `attributes` y `rules` quedan vacíos: están marcados como TODO porque
  requieren revisar `SBQQ__ConfigurationAttribute__c` y las reglas de
  precio/producto, que mezclan configuración declarativa con lógica en
  fórmulas o Apex.

## Adaptador de Industries CPQ/EPC

Todavía no implementado. Si el origen es Industries (`vlocity_cmt__`),
`discover.py` lo señala pero no hay extractor específico: los objetos y la
API difieren bastante de SBQQ (DataPacks, `vlocity_cmt__Product2`
attributes vía JSON en vez de registros separados, OmniScripts para la
configuración). Se añade como `extract_epc.py` +
`adapt_epc_to_canonical.py` siguiendo el mismo patrón cuando haga falta.

**`classify_gaps.py`**
- Aplica las reglas de `docs/mapping-sbqq-rlm.md` (documento editable, no
  código): bundle→`transformable` con nota de rediseño de agrupamiento,
  `SBQQ__ProductOption__c`→`redesign` siempre, precio con `charge_type`
  desconocido→`review`, price/product rules y promociones→`review` siempre
  (no hay regla determinista segura para lógica arbitraria).
- Nunca decide `direct` para algo que en realidad requiere criterio: ante
  la duda, clasifica `review` en vez de adivinar.
- Verificado con un canónico sintético de 8 elementos antes de dejarlo en
  el repo (2 direct, 3 transformable, 1 redesign, 2 review) — no probado
  todavía contra datos reales de un org.

## Siguiente etapa: generador de carga

Con el manifiesto de migración cerrado (agente `revenue-cloud-cpq-migration`
sobre `review_queue.json` + `canonical.classified.json`), falta el paso que
genera los CSV/JSON de carga hacia Revenue Cloud, ordenados por dependencias
(categorías → atributos → productos → selling models → bundles/componentes
→ pricebook entries → ajustes de precio), para cargar con Data Loader,
`sf data import` o Composite API — primero siempre en sandbox.
