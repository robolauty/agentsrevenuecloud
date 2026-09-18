# Demo Revenue Cloud (RLM) — Cliente industrial B2B (fabricante de piezas técnicas)
### Sector: manufactura / componentes técnicos (automoción, aeroespacial, alimentación) — venta a OEM/distribuidores

---

## 0. Resumen ejecutivo

El cliente fabrica piezas técnicas bajo especificación (planos, tolerancias, normativa) y vende a
OEMs/distribuidores mediante **contratos marco recurrentes** con forecast de volumen, pedidos JIT,
facturación a 60-90 días y revisiones anuales de precio/volumen con scorecard de proveedor.

Esto **no es una venta transaccional simple**: hay homologación de producto/proveedor, pricing por
tramos de volumen y por atributo técnico, un acuerdo marco que gobierna pedidos futuros, y un ciclo de
mejora continua con impacto en precio. Es el perfil ideal para **Revenue Cloud (RLM)**: catálogo con
atributos técnicos, pricing por volumen, Quote-to-Order recurrente contra un contrato marco, y
renovación anual con scorecard.

**Alcance de la demo (no metemos todo RLM, solo lo que valida los dolores reales):**
Catálogo + Pricing + Quote-to-Order + Contrato marco/Asset + Amendment/Renewal anual.
Dejamos fuera DRO y Billing por uso (no aportan a este dolor); si el cliente pregunta por facturación
a 60-90 días, se cubre con `PaymentTerm` (🟢) sin necesitar todo el módulo de Billing.

---

## 1. Mapeo del proceso comercial del cliente → ciclo de ingresos RLM

| # Paso del cliente | Dolor típico | Salto RLM | Patrón |
|---|---|---|---|
| 1. Generación de demanda (ferias, catálogos técnicos, fichas) | El lead llega sin estructurar; no hay trazabilidad del RFQ | Catálogo de producto (PCM) | P1 |
| 2. Cualificación técnica del lead (RFQ, planos, tolerancias) | El ingeniero de ventas valida "a mano" si el producto encaja | Guided selling / atributos técnicos | P1 + P2 |
| 3. Oferta técnico-comercial (coste, molde/utillaje, plazos, prototipo) | Cotizar piezas con molde/utillaje amortizado es manual y lento, errores de margen | Pricing (coste + tramos) + Quote | P4 + P5 |
| 4. Negociación y homologación de proveedor (ISO 9001, IATF 16949...) | El estado de homologación no está en el mismo sistema que la cotización | Atributo de calificación en el producto/cuenta (🔵) | — |
| 5. Firma de contrato marco (forecast de volumen) | El acuerdo recurrente no está modelado; cada pedido se negocia de cero | **Contrato marco = Asset / Enterprise Contract** | P6 + P7 |
| 6. Planificación de producción / pedidos JIT contra el marco | Los pedidos no heredan automáticamente el precio ya pactado en el marco | Quote-to-Order recurrente sobre el Asset | P6 |
| 7. Fabricación, calidad, logística (certificado por lote) | — (fuera de alcance CRM/RLM, se menciona pero no se construye) | — | — |
| 8. Facturación y cobro (60-90 días) | Condiciones de pago dispersas en Excel por cliente | `PaymentTerm`/`PaymentTermItem` | 🟢 |
| 9. Postventa: no conformidades, acciones correctivas, revisión anual precio/volumen | La revisión de precio anual se rehace desde cero cada año | **Amendment** sobre el Asset (ajuste de precio/volumen) | P7 |
| 10. Renovación del contrato marco + scorecard de proveedor | Renovar es "crear todo de nuevo"; no hay histórico ligado al Asset | **Renewal** con prorrateo/continuidad sobre el Asset | P7 |

---

## 2. Narrativa de la demo (los actos)

**Acto 1 — El RFQ se convierte en cotización técnica en minutos, no en días.**
El ingeniero de ventas recibe el RFQ (pieza + tolerancia + volumen anual estimado). Selecciona el
producto en el catálogo, que ya trae sus atributos técnicos (material, tolerancia, normativa aplicable)
y el estado de homologación. Configura cantidad y ve el precio ajustarse solo por tramo de volumen y por
coste de molde/utillaje amortizado. **WOW:** una cotización que antes tardaba días con Excel de costes,
aquí sale calculada y gobernada en segundos.

**Acto 2 — De la oferta al contrato marco, con forecast.**
La oferta ganadora se convierte con un clic en un **contrato marco (Order → Asset)** que representa el
acuerdo de suministro: precio pactado por tramo, vigencia, volumen previsto. **WOW:** el contrato marco
no es un PDF suelto, es un objeto vivo del que van a colgar todos los pedidos futuros.

**Acto 3 — Los pedidos JIT heredan el precio ya pactado, sin renegociar.**
El cliente lanza un pedido contra el contrato marco. El sistema no vuelve a cotizar desde cero: aplica
el precio y condiciones ya vigentes en el Asset. **WOW:** pedir contra un marco ya no es "cotizar otra
vez", es un pedido en un clic con el precio correcto garantizado.

**Acto 4 — Revisión anual de precio/volumen y renovación, sin rehacer nada.**
Llega la revisión anual: el volumen real superó el forecast, toca renegociar el tramo de precio. Se hace
como **Amendment** sobre el Asset existente, con el histórico intacto. **WOW:** renegociar un contrato
marco de un año para otro no es empezar de cero — es una modificación gobernada sobre lo que ya existe.

---

## 3. Configuration Manifest

### 3.1 Catálogo de producto (PCM) — 🟢 estándar / 🔵 atributos condicionados

| Elemento | Tipo | Detalle |
|---|---|---|
| `Product2` | 🟢 | Piezas técnicas (p.ej. "Componente inyectado ref. X"), servicios de molde/utillaje como producto independiente (amortizable) |
| `ProductClassification` | 🟢 | "Componente técnico inyectado" — define atributos heredados |
| `AttributeDefinition` + `AttributeCategory` | 🟢 | Material, tolerancia (mm), normativa aplicable (IATF 16949 / ISO 9001 / alimentaria), plazo de fabricación |
| `AttributePicklist`/`AttributePicklistValue` | 🟢 | Valores de material y normativa |
| Campo custom en `Account`/`Product2`: **Estado de homologación** (Pendiente / Auditoría en curso / Homologado) | 🔵 | Refleja el paso 4 (homologación de proveedor); condiciona si el producto es cotizable |
| `ProductCategory` | 🟢 | Familias: automoción, aeroespacial, alimentación |
| `ProductSellingModel` | 🟢 | "Contrato marco — Term" (recurrente, con vigencia anual) |

### 3.2 Pricing — 🟢 schedules / 🔵 Expression Set

| Elemento | Tipo | Detalle |
|---|---|---|
| `Pricebook2`/`PricebookEntry` | 🟢 | Precio base por pieza y por servicio de molde/utillaje |
| `CostBook`/`CostBookEntry` | 🟢 | Coste de producción para cálculo de margen |
| `PriceAdjustmentSchedule` + `PriceAdjustmentTier` | 🟢 | Tramos por volumen anual (p.ej. 0-10k uds, 10k-50k, 50k+) |
| `AttributeBasedAdjRule`/`AttributeBasedAdjustment` | 🔵 | Ajuste de precio por tolerancia exigida o normativa (a más exigencia, más coste) |
| `ExpressionSetDefinition` (pricing procedure) | 🔵 | Combina precio base + tramo de volumen + amortización de molde/utillaje + ajuste por atributo técnico en un único cálculo |

### 3.3 Guided selling / Quoting — 🟢 quote / 🔵 guided + docgen + approvals

| Elemento | Tipo | Detalle |
|---|---|---|
| Product Discovery + `DecisionTable` | 🔵 | El ingeniero de ventas responde: sector, tolerancia requerida, volumen estimado → recomienda producto y verifica si requiere homologación previa |
| `Quote`/`QuoteLineItem` | 🟢 | Cotización calculada por la pricing procedure |
| Approval flow | 🔵 | Aprobación si el descuento por volumen supera umbral o si el estado de homologación no es "Homologado" |
| Document Generation | 🔵 | Oferta técnico-comercial en PDF con condiciones de pago y plazos |

### 3.4 Contrato marco → Order/Asset — 🟢 nativo RLM

| Elemento | Tipo | Detalle |
|---|---|---|
| `Order`/`OrderItem` | 🟢 | Se genera desde la Quote ganadora → representa el contrato marco firmado |
| `Asset` | 🟢 | El contrato marco vivo: precio pactado, vigencia, volumen previsto (forecast) |
| `AssetStatePeriod` | 🟢 | Periodo de vigencia del contrato marco (anual) |
| `PaymentTerm`/`PaymentTermItem` | 🟢 | Condiciones de pago a 60/90 días |

### 3.5 Pedidos JIT contra el marco — 🟢

| Elemento | Tipo | Detalle |
|---|---|---|
| Nuevo `Order` referenciando el `Asset` del contrato marco | 🟢 | El pedido JIT hereda precio/condiciones ya pactadas, sin recotizar |

### 3.6 Revisión anual / renovación — 🟢/🔵

| Elemento | Tipo | Detalle |
|---|---|---|
| `AssetAction`/`AssetActionSource` (Amendment) | 🟢 | Ajuste de tramo de precio si el volumen real superó el forecast |
| Renewal sobre el `Asset` | 🟢 | Renovación del contrato marco para el siguiente periodo, con histórico y condiciones heredadas |
| Campo custom **Scorecard de proveedor** (calidad, plazo, no conformidades) en `Account` o relacionado al `Contract` | 🔵 | Alimenta la negociación de la renovación (no es objeto nativo RLM, se modela como campo/registro custom ligado) |

---

## 4. Clasificación resumen

- 🟢 **Estándar (mayoría):** Product2, atributos, Pricebook, Price Adjustment Schedules, Quote, Order,
  Asset, AssetStatePeriod, AssetAction, PaymentTerm.
- 🔵 **Custom declarativo:** Expression Set de pricing (combina volumen + molde/utillaje + atributo
  técnico), Decision Table de guided selling, approval flow, docgen, campo de estado de homologación,
  campo/registro de scorecard de proveedor.
- 🟠 **Código custom:** ninguno necesario para esta demo. Si en discovery real aparece un cálculo de
  amortización de molde muy específico que no se pueda modelar con Expression Set, sería el único
  candidato a Apex invocable — y solo entonces.

---

## 5. BUILD ORDER

```
1. Catálogo: Product2 (piezas + servicio molde/utillaje) + ProductClassification + Attributes
   (material, tolerancia, normativa) + campo Estado de homologación
2. ProductSellingModel "Contrato marco — Term" + Pricebook/PricebookEntry + CostBook
3. PriceAdjustmentSchedule/Tier (tramos de volumen) + AttributeBasedAdjustment (por tolerancia/normativa)
   + ExpressionSetDefinition (pricing procedure completa)
4. Guided selling: Product Discovery + Decision Table de recomendación/homologación
5. Quote + Approval flow (umbral descuento / no homologado) + Document Generation
6. Quote-to-Order → genera el contrato marco como Order/Asset con AssetStatePeriod + PaymentTerm
7. Pedido JIT: nuevo Order referenciando el Asset (hereda precio pactado)
8. Amendment sobre el Asset (revisión anual de tramo) + Renewal (siguiente periodo)
9. Datos semilla: catálogo poblado (2-3 piezas con atributos + 1 servicio de molde), 1 cliente
   homologado + 1 pendiente, 1 Quote calculada de ejemplo, 1 Asset activo (contrato marco) con
   histórico para poder mostrar el Amendment en vivo
```

---

## 6. Notas para la demo en vivo

- El WOW más fuerte para este cliente es el **Acto 3** (pedido JIT que hereda precio del contrato marco
  sin recotizar) y el **Acto 4** (renovación/amendment sin rehacer el contrato): son los dos dolores que
  el cliente describe explícitamente ("cada pedido se negocia de cero" y "la revisión anual se rehace").
- No construyas DRO ni Billing por uso: no están en el proceso descrito y sobredimensionarían la demo.
- Si el cliente es de automoción/aeroespacial, refuerza el campo de homologación (IATF 16949) como
  bloqueante de cotización — es un dolor sectorial reconocible al instante.
