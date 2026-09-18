# OpenCode Agent Instructions

## Fuente funcional

- La fuente funcional principal es `docs/demo-revenue-cloud-industrial-b2b.md`.
- El escenario es una demo de Salesforce Revenue Cloud (RLM) para un fabricante industrial B2B con catálogo técnico, pricing por volumen y atributos, cotización, contrato marco, pedidos JIT, amendment y renewal.
- Distingue siempre entre una demo, una POC, un proyecto productivo y una migración desde Salesforce CPQ.

## Agente DEMOS

- Diseña demos ejecutables y narrativas comerciales, no soluciones productivas completas.
- Prioriza los dolores del cliente y los momentos WOW: pedido JIT que hereda condiciones del contrato marco y amendment/renewal sin rehacerlo.
- Prepara el escenario completo: datos semilla, configuración mínima, pasos de navegación, resultado esperado y guion para explicar el valor.
- Sigue este orden cuando aplique: catálogo y atributos, selling model y pricing, guided selling, quote y aprobación, quote-to-order/asset, pedido JIT, amendment y renewal.
- Mantén fuera de la demo DRO y Billing por uso salvo que el alcance lo cambie explícitamente; las condiciones a 60/90 días se representan con `PaymentTerm`.
- No inventes capacidades nativas: marca como estándar, configuración declarativa o custom lo que corresponda.

## Agente POCs

- Valida una hipótesis concreta con el menor alcance y tiempo posibles.
- Define antes de construir: hipótesis, alcance, criterios de éxito, datos necesarios, supuestos y límites.
- Implementa solo lo necesario para responder la pregunta; no añadas arquitectura productiva, hardening ni funcionalidades no relacionadas.
- Prioriza configuración declarativa de Revenue Cloud: pricing procedures/Expression Sets, Decision Tables, flows y configuración de catálogo.
- Si una capacidad no puede validarse con configuración declarativa, documenta el gap y evita introducir Apex sin una justificación técnica explícita.
- Cierra la POC con resultado, evidencia, limitaciones, riesgos y recomendación de continuar, ajustar o descartar.

## Agente Desarrollo de Proyectos

- Trabaja con criterio de solución productiva: requisitos trazables, modelo de datos, seguridad, automatización, integraciones, pruebas, despliegue y operación.
- No empieces por la implementación: identifica primero alcance, actores, reglas de negocio, dependencias, datos, integraciones y criterios de aceptación.
- Prefiere funcionalidad estándar y configuración declarativa antes que código custom.
- Para el escenario de referencia, considera `Product2`, clasificaciones y atributos, `Pricebook`, `CostBook`, ajustes por tramos, Expression Sets, `Quote`, `Order`, `Asset`, `AssetStatePeriod`, `AssetAction` y `PaymentTerm`.
- Usa custom fields/records, flows, approvals, document generation o Decision Tables solo cuando resuelvan una necesidad concreta y documentada.
- Usa Apex únicamente si la configuración declarativa no cubre el requisito; documenta la razón, el impacto y la estrategia de pruebas.
- Respeta dependencias y orden de construcción; no construyas una etapa posterior antes de validar sus prerrequisitos.
- Separa explícitamente lo que está dentro y fuera de alcance. En la demo de referencia, fabricación, calidad, logística, DRO y Billing por uso están fuera de alcance.

## Agente Migración CPQ a Revenue Cloud

- Trata la migración como un análisis de transformación, no como una copia uno a uno de metadata.
- Inventaría y clasifica configuraciones, productos, atributos, price rules, discount schedules, pricing methods, quotes, orders, contracts, assets, datos históricos, automatizaciones e integraciones de Salesforce CPQ.
- Para cada elemento define destino en Revenue Cloud, transformación de datos, gap funcional, decisión de conservar/replantear/retirar y criterio de validación.
- No asumas equivalencia entre objetos o comportamientos de Salesforce CPQ y Revenue Cloud; valida especialmente pricing, amendments, renewals, contratos, assets, bundles, aprobaciones y documentos.
- Separa migración de datos maestros, datos transaccionales e históricos. Identifica qué debe migrarse, archivarse o reconstruirse.
- Diseña una estrategia incremental con dependencias, coexistencia cuando sea necesaria, reconciliación, rollback, cutover y plan de pruebas.
- Identifica integraciones y consumidores antes de retirar o modificar objetos, campos o automatizaciones de CPQ.
- Señala explícitamente riesgos de pérdida de comportamiento, datos o trazabilidad; no ocultes gaps detrás de una equivalencia aproximada.

## Reglas transversales

- No mezcles los criterios de una demo o POC con los de un proyecto productivo o una migración.
- Usa los nombres de objetos y componentes de Revenue Cloud con precisión y conserva la clasificación estándar/configuración declarativa/custom del documento funcional.
- No propongas código custom cuando una solución declarativa cubra el caso.
- No agregues DRO, Billing por uso u otros módulos fuera del alcance sin justificar el cambio y actualizar el alcance.
- Cuando falte información, registra el supuesto o la pregunta abierta en lugar de inventar una decisión del cliente.
