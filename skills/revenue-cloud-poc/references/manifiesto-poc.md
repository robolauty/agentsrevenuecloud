# Formato del MANIFIESTO-POC.md

El validador (`scripts/validate_manifest_poc.py`) depende de estos encabezados, prefijos de ID y
columnas. Español de España; nombres técnicos y API names en inglés. Tamaño en S/M/L, no horas.
Ejemplo completo en `assets/ejemplo-MANIFIESTO-POC.md`.

```markdown
# MANIFIESTO DE DESARROLLO (POC) — <Cliente o tema> — v<N>

**Estado de revisión:** BORRADOR
**Revisado por:** — · **Fecha de aprobación:** —
**Cliente:** … · **Sector:** … · **Zona fiscal:** Península (IVA 21%)
**Nube ancla:** Revenue Cloud (RLM) · **Nubes de apoyo:** … · **Org objetivo:** …
**Incertidumbre:** <la pregunta técnica o de negocio que hay que responder, en una frase>
**Restricciones del SE:** <literal> | Ninguna
**Reparto:** IA <n> (<x>%) · IA+Revisión <n> · Persona <n> · **Niveles:** 🟢 <n> · 🔵 <n> · 🟠 <n>

## 1. Contexto y necesidad de origen
| ID | Necesidad / duda del cliente | Origen |
|----|-------------------------------|--------|
| NEC-1 | <en lenguaje del cliente> | Brief |
| NEC-2 | … | Supuesto |

## 2. Hipótesis y experimento
**Hipótesis en una frase:** <qué creemos que es viable y bajo qué condición>

| ID | Hipótesis | Necesidad | Criterio de éxito | Si no se cumple / no concluyente |
|----|-----------|-----------|--------------------|-----------------------------------|
| HIP-1 | <enunciado verificable> | NEC-1 | <resultado observable y medible> | <qué evidencia haría falta en su lugar> |

| ID | Paso del experimento | Hipótesis | Entrada | Resultado esperado | Evidencia requerida |
|----|------------------------|-----------|---------|----------------------|------------------------|
| EXP-1 | <acción concreta a probar> | HIP-1 | <datos/condición de partida> | <qué debería pasar si la hipótesis es cierta> | <consulta, log, captura> |
| EXP-2 | … | HIP-1 | … | … | … |

## 3. Componentes
| ID | Paso | Componente | Tipo | Especificación | Nivel | Responsable | Motivo | Tamaño | Estado |
|----|------|------------|------|----------------|-------|-------------|--------|--------|--------|
| CMP-1 | EXP-1 | <nombre> | PricingRule | <condición y fórmula> | 🔵 | IA | — | S | Pendiente |
| CMP-2 | EXP-2 | Activar Revenue Cloud | Setup | Provisión/licencia en la org | 🟢 | Persona | Requiere licencia/provisión | S | Pendiente |
```
Reglas de la tabla (idénticas a `nespon-brief-to-demo/references/manifiesto.md`):
- `Nivel`: 🟢 default/config · 🔵 automatización o custom declarativo · 🟠 código.
- `Responsable`: `IA` | `IA+Revisión` | `Persona` (criterios en `ia-vs-persona.md`).
- `Motivo`: obligatorio si el responsable no es IA o el nivel es 🟠.
- `Tamaño`: S | M | L. `Estado`: Pendiente | Hecho | Bloqueado | Persona pendiente.

```markdown
## 4. Tareas de persona
### CMP-2 — Activar Revenue Cloud
- **Ruta:** Setup → … (el nombre del menú puede variar).
- **Valores:** —
- **Comprobar:** …
- **Desbloquea:** CMP-1

## 5. Datos de prueba
Spec: `datos/seed-spec.json` (generada con `fill_data.py`) · Qué representa cada caso: `datos/HISTORIA-DATOS.md`

| ID | Objeto | Registros | Contenido / valores clave | Pasos |
|----|--------|-----------|---------------------------|-------|
| DAT-1 | Product2 | 2 protagonistas + relleno | … | EXP-1 |

## 6. Orden de construcción
CMP-2 → CMP-1 → DAT-1 → ejecutar EXP-1 → ejecutar EXP-2

## 7. Supuestos y preguntas abiertas
- Supuesto: …
- Pregunta para el SE: …

## 8. Registro de cambios
- v1: versión inicial a partir del brief del <fecha>.
```

Aprobación: el SE cambia `Estado de revisión` a `APROBADO` y rellena `Revisado por` y
`Fecha de aprobación`. Sin eso la Fase 3 no arranca. La sección 9 (Resultado) la añade la Fase 3,
no se incluye en el borrador porque todavía no hay evidencia.
