# Formato del INFORME-VIABILIDAD.md

Se genera en la Fase 3, tras ejecutar (o intentar ejecutar) el experimento. Nunca se escribe antes
de tener evidencia real; si no hay org, el informe se queda en estado "preparación", sin resultado.

```markdown
# INFORME DE VIABILIDAD — <Cliente o tema> — v<N>

**Manifiesto de referencia:** MANIFIESTO-POC.md v<N> · **Org:** <alias, tipo> | Sin org conectada
**Fecha de ejecución:** <fecha> | — (no ejecutado)

## Resumen ejecutivo
<2-3 frases: qué se quería comprobar y qué se concluyó>

## Resultado por hipótesis
| ID | Hipótesis | Resultado | Evidencia | Limitaciones |
|----|-----------|-----------|-----------|---------------|
| HIP-1 | <enunciado> | 🟢 VALIDADA / 🟡 PARCIALMENTE VALIDADA / 🔴 NO VALIDADA / NO EJECUTADA / NO CONCLUYENTE | <consulta, log, captura concreta> | <bajo qué condiciones vale esto> |

## Pasos ejecutados
| ID | Paso | Resultado esperado | Resultado observado | Evidencia |
|----|------|----------------------|------------------------|-----------|
| EXP-1 | … | … | … | … |

## Acciones manuales realizadas / pendientes
<igual que 'Tareas de persona' del manifiesto, con su estado final>

## Limitaciones y condiciones
<edición/licencia necesaria, supuestos que quedaron sin confirmar, lo que NO se probó>

## Próximos pasos
<si procede: pasar a DEMO para mostrarlo al cliente, ampliar la POC, confirmar licencia, etc.>
```

Reglas:
- Cada hipótesis del manifiesto aparece con su resultado; nunca se omite ni se da por válida sin
  fila propia.
- "NO EJECUTADA" es el único resultado posible si no hubo org o autorización — nunca se infiere un
  resultado positivo o negativo sin haber corrido el experimento.
- La evidencia es verificable por un tercero (ID de componente, SOQL, salida de comando), nunca
  "se probó y funcionó" sin más.
