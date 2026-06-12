# User Stories — Convención de carpetas

Cada historia de usuario reside en su propia carpeta dentro de `user_stories/` con el nombre en snake_case.

## Estructura por historia

```
<nombre_historia>/
├── <nombre_historia>.md       ← Especificación de la historia de usuario (spec)
├── plan_<nombre_historia>.md  ← Plan derivado: reglas de negocio, criterios de aceptación, BDD
└── instrucciones_<tarea>.md   ← Tareas atómicas ejecutables por agentes (puede haber varias)
```

## Crear una nueva historia

1. Copiar `_plantilla.md` y `_plantilla_plan.md` en una nueva carpeta con el nombre de la historia.
2. Renombrar ambos archivos siguiendo la convención: `<nombre>.md` y `plan_<nombre>.md`.
3. Completar la spec con los datos de la historia.
4. Derivar el plan con reglas de negocio, criterios de aceptación y BDD.
5. Generar archivos `instrucciones_*.md` con pasos atómicos para ejecución por agente.

## Plantillas base

- `_plantilla.md` — Plantilla para la especificación de historia de usuario.
- `_plantilla_plan.md` — Plantilla para el plan de implementación.
