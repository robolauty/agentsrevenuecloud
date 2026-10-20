# INFORME DE VIABILIDAD — Bodegas Altiplano — v1

**Manifiesto de referencia:** MANIFIESTO-POC.md v1 · **Org:** Sin org conectada
**Fecha de ejecución:** — (no ejecutado)

## Resumen ejecutivo
Se preparó el experimento para comprobar si el motor de pricing estándar de Revenue Cloud resuelve
un descuento escalonado por tramos de cantidad. No se ha ejecutado todavía: falta conectar una org
con Revenue Cloud provisionado.

## Resultado por hipótesis
| ID | Hipótesis | Resultado | Evidencia | Limitaciones |
|----|-----------|-----------|-----------|---------------|
| HIP-1 | Un Price Adjustment Schedule con tramos por cantidad calcula el descuento correcto sin Apex | NO EJECUTADA | — | Pendiente de org con Revenue Cloud / RLM provisionado |

## Pasos ejecutados
| ID | Paso | Resultado esperado | Resultado observado | Evidencia |
|----|------|----------------------|------------------------|-----------|
| EXP-1 | Configurar Price Adjustment Schedule | El schedule se guarda y queda activo | — | — |
| EXP-2 | Generar Quote Line de 150 unidades | El precio cambia al tramo 100+ | — | — |
| EXP-3 | Comparar total sistema vs. cálculo manual | Coinciden (±0,01 €) | — | — |

## Acciones manuales realizadas / pendientes
- CMP-3 (verificar licencia Revenue Cloud): pendiente — requiere org conectada.

## Limitaciones y condiciones
Sin org conectada no se puede confirmar ni descartar la hipótesis. El resultado depende de la
edición/licencia real de Revenue Cloud de la org de destino.

## Próximos pasos
Conectar una org de demo/sandbox con Revenue Cloud provisionado y ejecutar la Fase 3 desde Claude
Code (`~/demos-nespon`, agente `demo-brief-architect`, skill `revenue-cloud-poc`).
