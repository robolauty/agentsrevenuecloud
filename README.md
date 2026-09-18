# Revenue Cloud Delivery Agents

Este repositorio define un flujo para transformar una petición comercial de un cliente en una demo, una POC, un proyecto de Salesforce Revenue Cloud o una migración desde Salesforce CPQ.

La fuente funcional de referencia es [`docs/demo-revenue-cloud-industrial-b2b.md`](docs/demo-revenue-cloud-industrial-b2b.md). Las reglas operativas de los agentes están en [`AGENTS.md`](AGENTS.md).

Las definiciones portables de los agentes están en [`agents/`](agents/). Los adaptadores para las herramientas están en `.claude/agents/` y `.opencode/agents/`.

## Objetivo

Cuando el cliente solicite una capacidad o proceso comercial, el flujo debe:

1. Entender la necesidad y el proceso afectado.
2. Clasificar correctamente el tipo de trabajo.
3. Generar un manifiesto de desarrollo.
4. Ejecutar el agente especializado.
5. Validar el resultado con criterios demostrables.
6. Entregar evidencia, limitaciones y siguientes pasos.

## Arquitectura

El orquestador principal recibe la petición y deriva el trabajo a uno de estos agentes:

```text
Orquestador
├── Agente DEMOS
├── Agente POCs
├── Agente Desarrollo de Proyectos
└── Agente Migración CPQ → Revenue Cloud
```

Las mismas cuatro definiciones están disponibles para Claude Code y OpenCode. Claude Code las descubre desde `.claude/agents/`; OpenCode desde `.opencode/agents/`. Ambos adaptadores remiten a la definición canónica en `agents/` y a las reglas comunes de `AGENTS.md`.

### Agente DEMOS

Construye escenarios ejecutables y narrativas comerciales. Debe incluir datos semilla, configuración mínima, pasos de navegación, resultado esperado y guion para explicar el valor al cliente.

En la demo de referencia, los momentos principales son:

- Cotización técnica con atributos y pricing por volumen.
- Conversión de la oferta en contrato marco mediante `Order`/`Asset`.
- Pedido JIT que hereda las condiciones del contrato marco.
- `Amendment` y `Renewal` sin rehacer el contrato.

### Agente POCs

Valida una hipótesis concreta con el menor alcance posible. Antes de construir debe definir hipótesis, alcance, criterios de éxito, datos, supuestos y límites.

El resultado debe incluir evidencia, limitaciones, riesgos y una recomendación: continuar, ajustar o descartar.

### Agente Desarrollo de Proyectos

Trabaja con criterio productivo: requisitos trazables, modelo de datos, seguridad, automatización, integraciones, pruebas, despliegue y operación.

No debe comenzar por la implementación. Primero debe validar alcance, actores, reglas, dependencias, datos, integraciones y criterios de aceptación.

### Agente Migración CPQ → Revenue Cloud

Analiza la transformación desde Salesforce CPQ sin asumir equivalencia uno a uno. Debe inventariar configuraciones, datos, automatizaciones e integraciones y definir para cada elemento destino, transformación, gap, decisión y criterio de validación.

Debe separar datos maestros, transaccionales e históricos, e incluir coexistencia, reconciliación, rollback, cutover y pruebas cuando aplique.

## Clasificación de solicitudes

| Situación del cliente | Tipo de trabajo | Agente |
|---|---|---|
| Quiere ver una capacidad conocida de Revenue Cloud | DEMO | Agente DEMOS |
| Existe una duda funcional o técnica concreta | POC | Agente POCs |
| La solución está aprobada para construcción productiva | PROYECTO | Agente Desarrollo de Proyectos |
| Existe una implementación Salesforce CPQ que debe transformarse | MIGRACIÓN | Agente Migración CPQ |
| Hay incertidumbre sobre la viabilidad | Primero POC | Agente POCs |

No se debe iniciar un proyecto productivo mientras exista una hipótesis crítica sin validar.

## Flujo operativo

```text
Petición del cliente
        ↓
Intake de negocio y alcance
        ↓
Clasificación DEMO / POC / PROYECTO / MIGRACIÓN
        ↓
Manifiesto de desarrollo
        ↓
Agente especializado
        ↓
Configuración y datos
        ↓
Validación funcional
        ↓
Evidencia y entrega al cliente
```

## Intake mínimo

Antes de generar el manifiesto, recoger:

- Necesidad de negocio.
- Proceso comercial afectado.
- Usuarios implicados.
- Capacidad u objetos de Revenue Cloud relacionados.
- Resultado esperado.
- Nivel de certeza requerido.
- Datos disponibles.
- Integraciones o sistemas implicados.
- Restricciones, fecha objetivo y fuera de alcance.

## Manifiesto de desarrollo

Cada solicitud debe producir un manifiesto homogéneo. Ejemplo:

```yaml
tipo: poc
nombre: pedido-jit-contra-contrato-marco
objetivo: >
  Validar que un pedido JIT hereda el precio y las condiciones
  desde un Asset que representa un contrato marco.
alcance:
  incluido:
    - Asset activo
    - precio pactado
    - nuevo Order contra Asset
    - PaymentTerm
  excluido:
    - DRO
    - Billing por uso
    - fabricación y logística
criterios_exito:
  - El pedido referencia el Asset correcto
  - El precio coincide con el contrato marco
  - No se requiere recotización manual
datos:
  - cliente homologado
  - producto técnico
  - contrato marco activo
  - forecast de volumen
configuracion_preferida:
  - funcionalidad estándar
  - configuración declarativa
riesgos:
  - validar el comportamiento exacto de herencia de precio
entregables:
  - configuración
  - datos semilla
  - pasos de ejecución
  - evidencia
  - gaps y recomendación
```

## Evolución entre etapas

Una solicitud puede avanzar de forma controlada:

```text
Petición
  ↓
POC para validar viabilidad
  ↓
DEMO para presentar el resultado
  ↓
Proyecto productivo si el cliente aprueba
```

Para una migración CPQ:

```text
Inventario CPQ
  ↓
POC sobre pricing, amendment o renewal
  ↓
Diseño de migración
  ↓
Construcción incremental
  ↓
Coexistencia y cutover
```

## Gates de control

Antes de entregar el resultado, comprobar:

- El objetivo y los criterios de éxito son claros.
- El alcance y el fuera de alcance están documentados.
- El tipo de trabajo es correcto.
- Se ha priorizado funcionalidad estándar y configuración declarativa.
- Los supuestos, gaps y riesgos están registrados.
- No se ha añadido Apex sin justificación técnica.
- No se han incorporado DRO, Billing por uso u otros módulos fuera de alcance sin aprobación explícita.
- La evidencia permite reproducir o explicar el resultado.

## Alcance actual de la demo

La demo de referencia cubre catálogo técnico, atributos, pricing por volumen, guided selling, quote, aprobación, quote-to-order, contrato marco, pedidos JIT, amendment y renewal.

Fabricación, calidad, logística, DRO y Billing por uso están fuera de alcance. Las condiciones de pago a 60/90 días se representan mediante `PaymentTerm`.

## Estado del repositorio

Actualmente el repositorio contiene documentación funcional y reglas de agentes. No hay código de aplicación, manifests de dependencias, pipeline CI, comandos de build o suite de tests verificables.

## Uso con Claude y OpenCode

- Claude Code carga `CLAUDE.md` y puede invocar los subagentes definidos en `.claude/agents/`.
- OpenCode carga `AGENTS.md` y descubre los subagentes definidos en `.opencode/agents/`.
- Claude App puede usar las definiciones de `agents/` como conocimiento del proyecto o como prompts reutilizables; no se debe asumir que ejecutará automáticamente los subagentes locales.
- Después de añadir o modificar agentes de OpenCode, reiniciar OpenCode para que recargue la configuración.
