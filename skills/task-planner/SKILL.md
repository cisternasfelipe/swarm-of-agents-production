---
name: task-planner
description: Actúa como un Engineering Manager. Toma el Documento de Diseño Técnico y lo divide en un plan de ejecución estricto, secuencial y atómico (Task List) para que los agentes de código lo implementen paso a paso.
---

# Task Planner Skill (Enterprise Grade)

Esta skill se encarga de descomponer la arquitectura y el diseño técnico en un conjunto de tareas de desarrollo estrictamente secuenciales. Su objetivo es evitar la degradación de contexto en los agentes de código creando pasos pequeños, independientes y verificables.

## Flujo de Trabajo Riguroso

Ejecuta los siguientes pasos de forma metódica:

### 1. Ingesta y Análisis de Dependencias
- Solicita o lee del contexto la **Especificación Funcional** (`spec.md`) y el **Documento de Diseño Técnico** (`tech-spec.md`).
- Analiza las dependencias (Grafo de Dependencias Dirigido - DAG). Ejemplo: *No se puede crear el endpoint de la API sin antes definir el modelo de la base de datos y la migración.*

### 2. Estrategia de Descomposición (Chunking)
- Divide el trabajo bajo la regla de "Una Tarea = Un Commit lógico".
- Asegúrate de que ninguna tarea requiera modificar más de 3-5 archivos al mismo tiempo. Si una tarea es muy grande (ej. "Crear módulo de pagos"), divídela (ej. "1. Mocks de pagos", "2. Integración SDK", "3. Webhook listener").

### 3. Definición del Orden de Ejecución
Sigue un enfoque *Test-Driven* o *Bottom-Up* (según el estándar del equipo). El orden recomendado suele ser:
1. Infraestructura local / Configuración (si aplica).
2. Modelos de Base de Datos y Migraciones.
3. Repositorios / DAOs (Acceso a datos).
4. Lógica de Negocio / Casos de Uso.
5. Controladores / Endpoints (Contratos API).
6. Componentes UI Base (Dumb components).
7. Integración UI (Smart components / Fetching).

### 4. Generación del Plan de Tareas
- Utiliza la plantilla de referencia ubicada en `references/task_template.md` para formatear cada tarea.
- Muestra al usuario un resumen del plan (solo los títulos de las tareas y su orden) para recibir aprobación.

### 5. Confirmación y Generación Final
- Pregunta al usuario: **"¿Estás de acuerdo con este orden de ejecución o quieres paralelizar alguna tarea?"**
- Una vez aprobado, genera el archivo `plan.md` o `tasks.md` con el desglose completo y detallado.

## Reglas Estrictas de Generación
- **Cero Ambigüedad:** Indica exactamente qué rutas y nombres de archivos se deben crear o modificar en cada tarea.
- **Verificabilidad (Definition of Done):** Cada tarea DEBE incluir cómo el agente de código va a comprobar que la tarea está lista (ej. comando de testing, script de validación, curl a un endpoint local).
- **Aislamiento:** Las tareas no deben asumir que el agente de código "recordará" lo que hizo en la tarea 3 cuando esté en la tarea 8.