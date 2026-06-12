---
name: spec-generator
description: Define una especificación de software a partir de una historia de usuario. Úsala cuando el usuario quiera definir o crear una spec, le pida revisar asunciones o quiera generar un documento de especificación detallado.
---

# Spec Generator Skill

Esta skill guía al usuario a través de la creación de una especificación de software detallada, iterando sobre las asunciones a partir de una historia de usuario inicial.

## Flujo de Trabajo

Sigue rigurosamente estos pasos cuando el usuario solicite crear una especificación (spec) a partir de una historia de usuario:

### 1. Recepción y Análisis Inicial
- Pide al usuario que te proporcione la **Historia de Usuario**.
- Una vez recibida, analiza la historia y "rellena los espacios en blanco" asumiendo los detalles no técnicos y funcionales necesarios para que el requerimiento tenga sentido completo.
- Muestra al usuario un **listado numerado** con todas tus asunciones.

### 2. Identificación de Correcciones
- Pide al usuario que te indique los **números** de las asunciones que **no le gustaron** o que considera incorrectas.

### 3. Iteración y Aclaración (Preguntas)
- Por cada número indicado por el usuario, debes hacerle una pregunta para redefinir esa asunción.
- Debes hacer las preguntas **una a una** (o usar la herramienta de interfaz de usuario si está disponible para agruparlas, pero siempre respetando la interactividad).
- En cada pregunta, **DEBES mostrar una barra de progreso** indicando cuántas preguntas llevas y cuántas faltan (ej. `Pregunta 1 de 2. [█████░░░░░] 50% completado.`).
- En cada pregunta, debes ofrecer **4 opciones** posibles (asunciones alternativas lógicas) y una **quinta opción** que dirá explícitamente `"Otra"`.
- Si el usuario selecciona "Otra", permítele especificar su propia respuesta o regla de negocio.

### 4. Confirmación
- Al finalizar todas las preguntas y ajustes, notifícale al usuario diciendo exactamente: **"Ya me encuentro listo para crear la especificación."**
- Espera la confirmación del usuario para proceder.

### 5. Generación de la Especificación
- Cuando el usuario confirme, genera el documento final de la especificación.
- **REQUISITO ESTRICTO:** La especificación generada **DEBE** contener en detalle las siguientes secciones (usa este mismo orden y títulos):
  1. Historia de usuario
  2. Objetivo
  3. Alcance
  4. Actores
  5. Precondiciones
  6. Disparador
  7. Flujo Principal
  8. Flujos Alternativos
  9. Reglas de negocio
  10. Criterios de aceptación
  11. Resultado esperado
  12. BDD (Behavior-Driven Development - escrito en formato Gherkin)

## Notas Adicionales
- Mantén el tono colaborativo, profesional y directo.
- Asegúrate de que los escenarios BDD cubran tanto el flujo principal como los flujos alternativos o mitigaciones de errores definidos en las asunciones.
