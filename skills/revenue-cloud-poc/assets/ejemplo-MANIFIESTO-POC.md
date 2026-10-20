# MANIFIESTO DE DESARROLLO (POC) — Bodegas Altiplano — v1

**Estado de revisión:** BORRADOR
**Revisado por:** — · **Fecha de aprobación:** —
**Cliente:** Bodegas Altiplano SA · **Sector:** Vino (bodega) · **Zona fiscal:** Península (IVA 21%)
**Nube ancla:** Revenue Cloud (RLM) · **Nubes de apoyo:** — · **Org objetivo:** SDO con Revenue Cloud provisionado
**Incertidumbre:** ¿El motor de pricing estándar de Revenue Cloud puede aplicar un descuento por volumen escalonado (no plano) sin desarrollo a medida?
**Restricciones del SE:** Solo mecanismos estándar de Pricing; nada de Apex para el cálculo
**Reparto:** IA 5 (71%) · IA+Revisión 1 · Persona 1 · **Niveles:** 🟢 2 · 🔵 4 · 🟠 0

## 1. Contexto y necesidad de origen
| ID | Necesidad / duda del cliente | Origen |
|----|-------------------------------|--------|
| NEC-1 | El comercial da descuentos por volumen "a ojo" en Excel; quieren que el sistema los calcule solo | Brief |
| NEC-2 | El descuento no es un % fijo: crece por tramos de cantidad | Brief |

## 2. Hipótesis y experimento
**Hipótesis en una frase:** El motor de pricing estándar puede resolver un descuento escalonado por tramos de cantidad sin código.

| ID | Hipótesis | Necesidad | Criterio de éxito | Si no se cumple / no concluyente |
|----|-----------|-----------|--------------------|-----------------------------------|
| HIP-1 | Un Price Adjustment Schedule con tramos por cantidad calcula el descuento correcto sin Apex | NEC-1, NEC-2 | Un pedido de 150 unidades aplica el tramo de descuento correspondiente y el total coincide con el cálculo manual | Si el motor no soporta tramos por cantidad en esta edición, queda NO VALIDADA y se documenta la alternativa (desarrollo o proceso manual) |

| ID | Paso del experimento | Hipótesis | Entrada | Resultado esperado | Evidencia requerida |
|----|------------------------|-----------|---------|----------------------|------------------------|
| EXP-1 | Configurar Price Adjustment Schedule con 3 tramos (1-49 / 50-99 / 100+) sobre un producto de prueba | HIP-1 | Producto "Vino Reserva Caja 6u" con precio base 42 € | El schedule se guarda y aparece activo en el Price Book Entry | Captura del schedule activo en Setup |
| EXP-2 | Generar una Quote Line de 150 unidades del producto de prueba | HIP-1 | Quote con el producto y cantidad 150 | El precio unitario de la línea cambia automáticamente al tramo 100+ | Quote Line con el precio por unidad aplicado, consulta SOQL del campo de precio |
| EXP-3 | Comparar el total calculado por el sistema contra el cálculo manual del tramo 100+ | HIP-1 | Mismos datos que EXP-2 | El total coincide (±0,01 € por redondeo) | Captura con ambos cálculos lado a lado |

## 3. Componentes
| ID | Paso | Componente | Tipo | Especificación | Nivel | Responsable | Motivo | Tamaño | Estado |
|----|------|------------|------|----------------|-------|-------------|--------|--------|--------|
| CMP-1 | EXP-1 | Producto de prueba | Product2 | "Vino Reserva Caja 6u", precio base 42 € | 🟢 | IA | — | S | Pendiente |
| CMP-2 | EXP-1 | Tramos de descuento | PriceAdjustmentSchedule | Tipo: Cantidad; tramos 1-49 (0%), 50-99 (5%), 100+ (12%) | 🔵 | IA | — | M | Pendiente |
| CMP-3 | EXP-1 | Verificar licencia Revenue Cloud | Setup | Comprobar PermissionSetLicense "Pricing" activo | 🟢 | Persona | Provisión/licencia, solo visible en Setup | S | Pendiente |
| CMP-4 | EXP-2 | Quote de prueba | Quote | Oportunidad y cuenta de prueba, Quote Line del producto CMP-1 | 🔵 | IA | — | S | Pendiente |
| CMP-5 | EXP-2 | Línea con cantidad 150 | QuoteLineItem | Quantity = 150 sobre CMP-1 | 🟢 | IA | — | S | Pendiente |
| CMP-6 | EXP-3 | Consulta de verificación | Report | Report sobre QuoteLineItem: cantidad, precio unitario, total | 🔵 | IA+Revisión | Confirmar que el filtro y las columnas muestran el dato correcto | S | Pendiente |
| CMP-7 | EXP-1 | Permisos de prueba | PermissionSet | CRUD sobre Product2, Quote, QuoteLineItem; acceso a Pricing | 🔵 | IA | — | S | Pendiente |

## 4. Tareas de persona
### CMP-3 — Verificar licencia Revenue Cloud
- **Ruta:** Setup → Company Settings → Permission Set Licenses (el nombre del menú puede variar).
- **Valores:** —
- **Comprobar:** aparece una licencia con "Pricing" o "Revenue" asignada y disponible.
- **Desbloquea:** CMP-2

## 5. Datos de prueba
Spec: `datos/seed-spec.json` (generada con `fill_data.py`) · Qué representa cada caso: `datos/HISTORIA-DATOS.md`

| ID | Objeto | Registros | Contenido / valores clave | Pasos |
|----|--------|-----------|---------------------------|-------|
| DAT-1 | Account, Opportunity | 1 protagonista | Cuenta de prueba "Distribuidor Test SL" con una oportunidad abierta | EXP-2 |

## 6. Orden de construcción
CMP-3 → CMP-7 → CMP-1 → CMP-2 → DAT-1 → CMP-4 → CMP-5 → CMP-6 → ejecutar EXP-1 → ejecutar EXP-2 → ejecutar EXP-3

## 7. Supuestos y preguntas abiertas
- Supuesto: la org objetivo tiene Revenue Cloud (RLM) provisionado, no solo Sales Cloud con CPQ heredado.
- Pregunta para el SE: ¿los tramos reales son los de este ejemplo o el cliente los ha definido en el brief?

## 8. Registro de cambios
- v1: versión inicial a partir de la duda planteada por el comercial.
