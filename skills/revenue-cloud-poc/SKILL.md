---
name: revenue-cloud-poc
description: >
  Convierte el brief o la duda técnica de un cliente sobre Salesforce Revenue Cloud en una POC:
  manifiesto de desarrollo que separa lo que construye la IA de lo que debe hacer una persona, y un
  informe de viabilidad que concluye si la hipótesis queda validada, con evidencias. Reutiliza el
  método de `nespon-brief-to-demo` (reparto IA/IA+Revisión/Persona, niveles 🟢/🔵/🟠, datos de prueba
  ficticios) pero sustituye escenas-y-wow por pasos de experimento ligados a una hipótesis, y el
  pitch por un informe de viabilidad. Úsala SIEMPRE que el usuario quiera comprobar si algo "se
  puede hacer" en Revenue Cloud, validar una hipótesis técnica o de pricing/configurador, o pida
  explícitamente una POC en vez de una demo.
---

# Revenue Cloud — del brief/incertidumbre a la POC

Esta skill **extiende** `nespon-brief-to-demo`: una POC responde **"¿es viable este comportamiento y
bajo qué condiciones?"**, no "¿cómo gusta esto al cliente?". Antes de usarla, ten cargadas:

- `nespon-brief-to-demo` — de ahí reutilizas tal cual: `references/ia-vs-persona.md` (reparto),
  `references/impacto.md` (niveles 🟢/🔵/🟠), `references/datos-demo.md` y `scripts/fill_data.py`
  (datos de prueba).
- `nespon-demo-builder` — playbook `references/nubes/revenue-cloud.md` (objetos y escenas
  canónicas de RLM) y, para la Fase 3 real, `references/ejecucion-en-org.md`.

## Cuándo POC y no DEMO
Si no hay una incertidumbre técnica concreta que comprobar, es una DEMO: usa `nespon-brief-to-demo`
directamente. Señales de POC: "¿se puede calcular el precio con...?", "¿el configurador soporta...?",
"necesitamos comprobar si...", una dependencia técnica dudosa, un modelo de pricing no estándar.

## FASE 1 — Diseño (no toca la org)

### 1.1 Identificar la incertidumbre
Qué aspecto concreto hay que comprobar (`references/brief.md` de `nespon-brief-to-demo` para extraer
el resto del contexto: cliente, sector, zona fiscal, restricciones).

### 1.2 Formular hipótesis (`HIP-n`)
Una frase verificable por hipótesis. "El mecanismo de pricing estándar permite calcular el precio
usando características del producto y coste de instalación." Nunca la des por probada porque la
documentación mencione una capacidad relacionada.

### 1.3 Diseñar los pasos del experimento (`EXP-n`)
Cada paso liga a ≥1 `HIP`, con condición de entrada, acción y **resultado esperado observable**
(no "funciona correctamente"). Excluye expresamente: interfaces comerciales completas innecesarias,
migraciones de datos completas, todo lo que no sirva para comprobar la hipótesis.

### 1.4 Componentes y reparto
Igual que en `nespon-brief-to-demo`: tabla de componentes con nivel 🟢/🔵/🟠 y responsable
IA / IA+Revisión / Persona (`references/ia-vs-persona.md`), tareas de persona con ruta, valores,
comprobación y qué desbloquean.

### 1.5 Datos de prueba
Sigue `references/datos-demo.md` de `nespon-brief-to-demo`, pero el foco es que cada caso de prueba
tenga los datos exactos que el experimento necesita, no "contar una historia". Mismo generador
(`fill_data.py`), mismas reglas (ficticios, `@example.com`, fechas relativas).

### 1.6 Validar y entregar para revisión
```bash
python3 <skill-dir>/scripts/validate_manifest_poc.py poc-<slug>/MANIFIESTO-POC.md
```
Corrige los errores. Deja `Estado de revisión: BORRADOR` y presenta un resumen corto: hipótesis,
pasos, % de componentes IA, tareas de persona, supuestos. **Para aquí. No construyas nada.**

Formato exacto: `references/manifiesto-poc.md`. Ejemplo: `assets/ejemplo-MANIFIESTO-POC.md`.

## FASE 2 — Revisión (el SE)
Igual que en `nespon-brief-to-demo`: el SE revisa, puede pedir cambios (nueva versión con registro
de cambios), y aprueba poniendo `Estado de revisión: APROBADO` con su nombre, o confirmándolo en la
conversación.

## FASE 3 — Ejecución del experimento (solo con org y sf CLI — Claude Code / Vibes)

1. **Puerta:** `validate_manifest_poc.py --gate`; sin `APROBADO` no se toca la org.
2. Pre-flight de `nespon-demo-builder` (org confirmada, licencias de Revenue Cloud/RLM).
3. Construye los componentes en el orden del manifiesto (IA / IA+Revisión / Persona, igual que
   `construccion.md` de `nespon-brief-to-demo`).
4. Carga los datos de prueba (`fill_data.py` → `build_seed.py` → `sf data import tree`).
5. **Ejecuta cada paso del experimento** y registra el resultado real observado frente al esperado,
   con su evidencia (consulta, captura, log).
6. Clasifica cada hipótesis (ver abajo) y genera `INFORME-VIABILIDAD.md`
   (`references/informe-viabilidad.md`).

Si no hay org conectada, la Fase 3 no se ejecuta: entrega el diseño con estado **PREPARADA, NO
EJECUTADA** y nunca afirmes un resultado de hipótesis sin haberla ejecutado.

## Resultado de cada hipótesis
- 🟢 **VALIDADA** — evidencia suficiente de cumplimiento.
- 🟡 **PARCIALMENTE VALIDADA** — se cumple con limitaciones documentadas.
- 🔴 **NO VALIDADA** — evidencia de incumplimiento.
- **NO EJECUTADA** — no se ha realizado el experimento (p. ej. sin org).
- **NO CONCLUYENTE** — evidencia insuficiente para decidir.

Nunca clasifiques como validada una hipótesis por el mero hecho de haber generado documentación o
código. Este resultado es distinto del nivel 🟢/🔵/🟠 de los componentes (eso mide cuánto es custom,
no si la hipótesis se cumple).

## Ficheros que genera (en `poc-<cliente-o-tema-slug>/`)
| Fichero | Fase | Para quién |
|---|---|---|
| `MANIFIESTO-POC.md` | 1 | El SE (revisión) y quien ejecute la Fase 3 |
| `datos/seed-spec.json`, `datos/HISTORIA-DATOS.md` | 1 | Carga y pruebas |
| `INFORME-VIABILIDAD.md` | 3 | El SE y el cliente técnico: resultado de cada hipótesis con evidencias |

## Referencias
| Archivo | Cuándo |
|---|---|
| `references/manifiesto-poc.md` | 1.2–1.6: formato exacto del manifiesto de POC |
| `references/informe-viabilidad.md` | Fase 3: formato del informe de resultado |
| (de `nespon-brief-to-demo`) `references/ia-vs-persona.md`, `impacto.md`, `datos-demo.md` | 1.4–1.5 |
| (de `nespon-demo-builder`) `references/nubes/revenue-cloud.md`, `ejecucion-en-org.md` | diseño y Fase 3 |

| Script | Para qué |
|---|---|
| `scripts/validate_manifest_poc.py` | Valida `MANIFIESTO-POC.md` antes de entregarlo y antes de ejecutar |
