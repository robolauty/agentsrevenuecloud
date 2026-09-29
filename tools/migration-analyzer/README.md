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
agente revenue-cloud-cpq-migration → resuelve review_queue.json y marca reviewed_by_human=true
        ↓
generate_load.py        → genera SObject Tree + plan.json solo con lo revisado y aprobado
        ↓
sf data import tree --plan plan.json --target-org <sandbox>
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

# 6. Tras resolver review_queue.json (agente/humano) y marcar
#    reviewed_by_human=true en canonical.classified.json, generar la carga
#    (--include-price-adjustments si hay tramos de precio ya resueltos en
#    prices[].tiers)
python3 scripts/generate_load.py \
    --canonical output/cliente-sandbox/canonical.classified.json \
    --mapping config/load_mapping.json \
    --out output/cliente-sandbox/load \
    --include-price-adjustments

# 7. Solo contra sandbox
sf data import tree --plan output/cliente-sandbox/load/plan.json --target-org cliente-sandbox
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
  `SBQQ__ConfigurationAttribute__c`, `SBQQ__DiscountSchedule__c`,
  `SBQQ__DiscountTier__c`.
- Los campos por objeto salen del `describe`, no de una lista fija, así que
  incluye automáticamente los campos custom del cliente.
- **No incluye todavía**: `SBQQ__PriceRule__c`, `SBQQ__ProductRule__c`,
  históricos de `Quote`/`Order`/`Contract`/`Asset`. Se añaden ampliando la
  lista `OBJECTS` cuando el flujo básico esté validado.

**`adapt_sbqq_to_canonical.py`**
- Mapea 1:1 lo simple: producto, categoría, pricebook, precio, y la
  relación bundle→componente de `SBQQ__ProductOption__c`.
- `SBQQ__DiscountSchedule__c` + `SBQQ__DiscountTier__c` → `rules`
  (`rule_type="discount"`), con los tramos anidados en `conditions`. **No**
  intenta enlazar automáticamente el schedule a un producto o
  `PricebookEntry`: ese campo de vínculo varía según cómo esté configurado
  cada org, así que se deja para que el agente lo resuelva en la revisión
  y, si corresponde, vuelque los tramos en `prices[].tiers` del elemento
  correcto.
- Marca todo con `migration.classification = "pending"` — este script no
  decide qué es `direct`/`transformable`/`redesign`, solo normaliza. Esa
  clasificación es el siguiente paso (análisis de gaps).
- `attributes` queda vacío: está marcado como TODO porque requiere revisar
  `SBQQ__ConfigurationAttribute__c`, que mezcla configuración declarativa
  con lógica en fórmulas.

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

**`generate_load.py`**
- Genera ficheros en formato [SObject Tree](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_composite_tree_sobject_collections.htm)
  (`01_ProductCategory.json`, `02_Product2.json`, ...) + un `plan.json`
  para `sf data import tree`. Las relaciones (producto→categoría,
  precio→producto/pricebook) se resuelven por referencia (`@ref`), sin
  necesitar campos de external id en el destino.
- **Solo incluye lo que ya pasó por revisión**: exige
  `classification in (direct, transformable)` Y `reviewed_by_human == true`
  en cada elemento. Todo lo demás queda fuera y listado en
  `load_summary.md` con el motivo — no se descarta en silencio ni se
  fuerza una carga de algo no aprobado.
- Los componentes de bundle (`ProductRelatedComponent`) **nunca** se
  generan aquí: `classify_gaps.py` los marca siempre `redesign`, y ese
  rediseño es una decisión de agrupamiento (`ProductComponentGroup`) que
  toma el agente/humano en el manifiesto, no este script.
- `ProductSellingModel` solo se genera con `--include-selling-models`, y
  aun así queda marcado en el resumen como "requiere validación manual":
  SBQQ no tiene un dato equivalente, así que el tipo (`Evergreen`,
  `OneTime`, ...) es una inferencia sobre `selling_model` del canónico,
  no un valor migrado.
- Los nombres de objeto/campo del destino viven en
  `config/load_mapping.json`, no hardcodeados en el script. Los bloques
  marcados `"verify": true` (selling models, `ProductCategoryProduct`,
  componentes) dependen de la versión de Revenue Cloud del org destino:
  **contrastar contra `sf sobject describe` del destino antes de una
  carga real**, no asumir que el nombre de campo es correcto.
- Verificado con el mismo canónico sintético (tras simular
  `reviewed_by_human=true` en lo aprobado): generó `ProductCategory`,
  `Product2`, `Pricebook2`, `PricebookEntry` y omitió correctamente el
  precio con `charge_type` desconocido, listándolo en `load_summary.md`.

**`generate_load.py --include-price-adjustments`**
- Con `--include-price-adjustments`, genera `PriceAdjustmentSchedule` (uno
  por precio con `tiers`) + `PriceAdjustmentTier` (uno por tramo),
  enlazados al `PricebookEntry` correspondiente por referencia.
- Igual que los selling models: queda **siempre** marcado como "requiere
  validación manual" en `load_summary.md`, porque el nombre de objeto y de
  campos (`load_mapping.json`: `price_adjustment_schedule`,
  `price_adjustment_tier`, ambos `"verify": true`) no está confirmado
  contra un org real, y el tipo de tramo (`TieredExclusive` por defecto)
  es una decisión funcional, no técnica.
- Los tramos (`tiers`) no salen automáticamente de `adapt_sbqq_to_canonical.py`:
  los discount schedules de SBQQ se capturan en `rules` sin enlazar (ver
  arriba), así que hace falta que la revisión del agente/humano vuelque
  los tramos correctos en `prices[].tiers` antes de que este flag tenga
  algo que generar.
- Verificado con datos sintéticos: 2 tramos generados correctamente,
  referencias resueltas en cadena `PricebookEntry` → `PriceAdjustmentSchedule`
  → `PriceAdjustmentTier`.

## Adaptador de Industries CPQ/EPC

Todavía no implementado. Si el origen es Industries (`vlocity_cmt__`),
`discover.py` lo señala pero no hay extractor específico: los objetos y la
API difieren bastante de SBQQ (DataPacks, `vlocity_cmt__Product2`
attributes vía JSON en vez de registros separados, OmniScripts para la
configuración). Se añade como `extract_epc.py` +
`adapt_epc_to_canonical.py` siguiendo el mismo patrón cuando haga falta.

## Siguiente etapa: componentes de bundle y atributos

`generate_load.py` cubre catálogo, precio simple y ahora tramos de precio
(`--include-price-adjustments`). Quedan fuera, como siguiente pieza a
construir:

- Componentes de bundle, una vez que el manifiesto de migración defina el
  agrupamiento en `ProductComponentGroup` (no hay forma determinista de
  generarlo sin esa decisión).
- Atributos (`SBQQ__ConfigurationAttribute__c` → `AttributeDefinition`),
  todavía no procesados por `adapt_sbqq_to_canonical.py` (sí extraídos por
  `extract_sbqq.py`, pero `attributes` sigue vacío en el canónico).
- Enlazar `SBQQ__DiscountSchedule__c` a producto/`PricebookEntry`
  automáticamente cuando se confirme, con casos reales, cuál es el campo
  de vínculo — hoy queda siempre en `rules` para revisión manual.
