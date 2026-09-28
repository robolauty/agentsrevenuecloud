# Mapeo de referencia: Salesforce CPQ (SBQQ) → Revenue Cloud (RLM)

Este documento es la base de conocimiento que usa `scripts/classify_gaps.py`
para clasificar cada elemento del modelo canónico. No es exhaustivo: se
amplía a medida que se validan casos reales contra la documentación vigente
de Revenue Cloud (el modelo de objetos cambia entre releases, así que esto
se revisa por proyecto, no se da por hecho de memoria).

Clasificación usada en todo el documento:

- **direct** — mismo objeto o equivalente casi 1:1, sin rediseño funcional.
- **transformable** — el dato migra, pero requiere una transformación
  estructural (nuevo objeto relacionado, split de un campo en varios).
- **redesign** — no hay equivalente directo; hace falta una decisión de
  diseño en el destino.
- **review** — no se puede decidir sin mirar el registro concreto (falta
  contexto, o la regla depende de datos que no están en el canónico).

## Catálogo

| SBQQ | Revenue Cloud (RLM) | Clasificación | Nota |
|---|---|---|---|
| `Product2` (simple, activo) | `Product2` + `ProductSellingModel` | transformable | RLM exige un `ProductSellingModel` explícito (one_time/evergreen/term/usage) que en CPQ vive disperso en varios campos (`SBQQ__SubscriptionType__c`, `SBQQ__SubscriptionPricing__c`, `SBQQ__SubscriptionTerm__c`). |
| `Product2` (bundle) | `Product2` + `ProductComponentGroup` + `ProductRelatedComponent` | transformable | Estructura distinta a CPQ: RLM agrupa componentes en `ProductComponentGroup`, no en `SBQQ__ProductFeature__c`. Requiere rediseño del agrupamiento, no solo copia de datos. |
| `Product2` (class/virtual) | — | review | Revisar caso por caso; no siempre tiene equivalente limpio. |
| `ProductCategory` | `ProductCategory` | direct | Jerarquía compatible. |
| `Pricebook2` | `Pricebook2` + `CostBook` | direct | El objeto Pricebook se mantiene; `CostBook` es nuevo y se configura aparte (no viene de CPQ). |
| `PricebookEntry` (charge_type conocido) | `PricebookEntry` + `PriceAdjustmentSchedule` si hay tramos | transformable | Precio base migra directo; los descuentos por volumen requieren `PriceAdjustmentSchedule`/`PriceAdjustmentTier`. |
| `PricebookEntry` (charge_type = unknown) | — | review | No se puede clasificar sin saber si es recurrente, one-time o de uso. Revisar `SBQQ__ChargeType__c` / `SBQQ__PricingMethod__c` del producto padre. |
| `SBQQ__ProductOption__c` | `ProductRelatedComponent` | redesign | El modelo de opciones/features de CPQ no mapea campo a campo; hay que rediseñar la agrupación como `ProductComponentGroup`. |
| `SBQQ__ConfigurationAttribute__c` | `AttributeDefinition` + `ProductAttributeDefinition` | transformable | Migra el valor y el tipo; picklists dependientes (`SBQQ__Dependency__c`) requieren revisión manual porque RLM los modela distinto. |
| `SBQQ__PriceRule__c` con acción declarativa simple | `PriceAdjustmentSchedule` / `Expression Set` | transformable | Solo si la regla es condición→ajuste de precio simple. |
| `SBQQ__PriceRule__c` con fórmula Apex o lógica compleja | — | redesign | Sin equivalente automático; hay que rediseñar con Expression Sets o Decision Tables. |
| `SBQQ__ProductRule__c` (validación/selección declarativa) | Decision Table / validación de configurador | transformable | |
| `SBQQ__DiscountSchedule__c` | `PriceAdjustmentSchedule` (tipo tiered) | transformable | |
| Apex custom (clases/triggers sobre pricing o configuración) | — | redesign | Siempre requiere rediseño; nunca se asume equivalencia automática. |

## Qué NO decide este documento

- Si conviene coexistencia CPQ/RLM durante la migración.
- Estrategia de datos históricos (quotes, contratos, assets ya facturados).
- Rollback y cutover.

Esas decisiones son del **informe de gaps** completo (agente
`revenue-cloud-cpq-migration`), que usa esta tabla como insumo, no como
sustituto del análisis.
