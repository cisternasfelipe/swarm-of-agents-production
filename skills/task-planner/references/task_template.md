# Plantilla de Tarea Atómica (Task Template)

*El plan generado debe contener una lista de tareas siguiendo exactamente esta estructura por cada ítem.*

### [Tarea X]: [Nombre descriptivo de la tarea, ej. Creación del Modelo de Usuario y Migración]

**1. Objetivo:**
[Descripción de 1-2 líneas sobre lo que se va a lograr y por qué].

**2. Dependencias:**
- [Lista de Tareas previas que deben estar completadas (ej. Tarea 1, Tarea 2)].
- [Archivos que el agente NECESITA leer para entender el contexto (ej. `src/config/db.ts`)].

**3. Archivos a Modificar / Crear:**
- `ruta/exacta/archivo_nuevo.ts` (Crear)
- `ruta/exacta/archivo_existente.ts` (Modificar)

**4. Instrucciones de Implementación:**
- [Paso 1: ej. Definir el esquema de Prisma para el modelo User].
- [Paso 2: ej. Asegurar que la contraseña use el tipo de dato correcto].
- [Paso 3: ej. Generar la migración de base de datos sin aplicarla en producción].

**5. Criterios de Aceptación (Definition of Done):**
- [ ] El código compila sin errores de linting (`npm run lint`).
- [ ] Se ha creado el archivo de test unitario `ruta/exacta/archivo.test.ts`.
- [ ] El test unitario pasa correctamente ejecutando el comando `npm run test:watch`.

---