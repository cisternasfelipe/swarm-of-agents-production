# Plan de Implementación para HU-002: Tests del Login

## 1. Visión General del Plan:

Agregar una suite de tests con `bun:test` al backend en dos niveles: (a) tests unitarios de los utils puros (`jwt`, `cookies`, `authToken`, `auth`, `cors`) y (b) tests de integración HTTP que levantan el servidor real de producción en proceso (puerto efímero) contra una base PostgreSQL de test separada (`construerp_test`), cubriendo todos los escenarios BDD de la historia de login. Se hace un único refactor mínimo de producción: extraer la creación del servidor a `src/server.ts` (`createServer(port)`) para que los tests reutilicen el routing exacto (CORS, 404, 500) sin duplicarlo.

---

## 2. Reglas de negocio

*   **R1 - Aislamiento de datos:** Los tests jamás leen ni escriben la base de desarrollo `construerp_db`. Toda la integración corre contra `construerp_test`, con una guarda de dos capas que aborta la suite si la conexión no apunta a la base de test (verificación del string de `DATABASE_URL` + `SELECT current_database()`).
*   **R2 - Sin mocks de módulos:** Prohibido `mock.module` de bun:test (sus registros persisten para todo el proceso y contaminan otros archivos de test). Los utils se prueban como funciones puras; la lógica de servicio/controlador se prueba de extremo a extremo.
*   **R3 - Determinismo:** Los tests fuerzan su propio entorno (JWT secret de test conocido, flag de fuerza bruta apagado por defecto, origen CORS fijo) vía un preload que se ejecuta antes que cualquier test, y cada test parte de una tabla `users` truncada con fixtures propias.
*   **R4 - Cobertura BDD:** Cada criterio de aceptación de la HU de login (login exitoso, mensaje genérico, fuerza bruta tras flag, auditoría, rotación, logout, CORS) debe tener al menos un test de integración que lo verifique.
*   **R5 - Cero dependencias nuevas:** Solo `bun:test` y las APIs de Bun ya disponibles.

---

## 3. Criterios de aceptación

*   `bun run test:unit` pasa en verde sin Docker ni base de datos.
*   `bun run test:integration` aprovisiona `construerp_test` (idempotente) y pasa en verde con el contenedor Postgres corriendo.
*   `bun run test` ejecuta ambas suites en procesos separados y termina con exit 0.
*   Tras correr la suite completa, el contenido de `construerp_db` queda intacto.
*   Una regresión provocada (cambiar el mensaje genérico esperado) hace fallar exactamente los tests que lo asertan (demo negativa documentada).
*   `bun run start` sigue funcionando igual tras el refactor de `src/index.ts`.

---

## 4. Resultado esperado

El desarrollador dispone de `bun run test` como red de seguridad del login: ~34 casos unitarios y ~22 de integración que validan el contrato HTTP completo (status, mensajes byte a byte, cookies con sus atributos exactos, rotación de tokens, auditoría en archivo y CORS), ejecutables localmente en menos de un minuto, sin riesgo alguno para los datos de desarrollo.

---

## 5. BDD (Behavior-Driven Development)

### Feature: Suite de tests automatizados del login

#### Scenario: Tests unitarios sin infraestructura
*   **Given** un entorno con Bun y dependencias instaladas
*   **When** el desarrollador ejecuta `bun run test:unit`
*   **Then** los tests de `jwt`, `cookies`, `authToken`, `auth` y `cors` pasan sin conexión a base de datos

#### Scenario: Tests de integración con aprovisionamiento automático
*   **Given** el contenedor `construerp-db` está healthy
*   **When** el desarrollador ejecuta `bun run test:integration`
*   **Then** se crea (si no existe) y migra la base `construerp_test`
*   **And** los escenarios HTTP del login pasan contra el servidor real

#### Scenario: La suite protege la base de desarrollo
*   **Given** la base `construerp_db` con el usuario seed
*   **When** corre cualquier test de integración
*   **Then** la conexión se verifica contra `construerp_test` y la suite aborta si no coincide

#### Scenario: La suite detecta regresiones
*   **Given** un cambio que altera el mensaje de error genérico del login
*   **When** se ejecuta la suite de integración
*   **Then** los tests del mensaje genérico fallan con diff legible

---

## 6. Tareas Detalladas:

*   **Tarea 1:** Infraestructura de test
    *   **Sub-tareas:**
        *   Crear `bunfig.toml`, `tests/preload.ts`, `tests/helpers/constants.ts`
        *   Refactor `src/index.ts` → `src/server.ts` con `createServer(port)`
        *   Crear `scripts/setup-test-db.ts` (crea y migra `construerp_test`, idempotente)
        *   Actualizar `tsconfig.json` (include) y `package.json` (scripts test)
    *   **Estimación:** 1 hora

*   **Tarea 2:** Tests unitarios (5 archivos en `tests/unit/`)
    *   **Sub-tareas:** `jwt`, `cookies`, `authToken`, `auth`, `cors`
    *   **Estimación:** 1.5 horas

*   **Tarea 3:** Helpers de integración (`tests/integration/helpers/`)
    *   **Sub-tareas:** `db.ts` (guarda + fixtures SQL), `fixtures.ts` (usuario y hash memoizado), `server.ts`, `http.ts`, `audit.ts`
    *   **Estimación:** 1 hora

*   **Tarea 4:** Tests de integración (5 archivos en `tests/integration/`)
    *   **Sub-tareas:** `login`, `refresh`, `logout`, `bruteforce`, `cors`
    *   **Estimación:** 2 horas

*   **Tarea 5:** Verificación completa y demo negativa
    *   **Estimación:** 0.5 horas

---

## 7. Consideraciones Técnicas:

*   **Tecnologías:** `bun:test` (runner, expect, lifecycle hooks), `Bun.serve` con puerto 0 (efímero), `Bun.SQL` (instancias explícitas para el setup de la DB de test), `Headers.getSetCookie()`.
*   **Dependencias:** HU-001 (login backend implementado), docker-compose con Postgres 17 corriendo.
*   **Riesgos:** (1) Momento exacto en que el `sql` global captura `DATABASE_URL` — mitigado con preload antes de toda conexión + guarda `current_database()` que aborta en el peor caso; (2) lentitud de argon2id (~100–500 ms por verificación) — mitigado con hash de fixture memoizado y timeouts generosos (15 s unit, 30 s integración, 60 s por test de fuerza bruta); (3) si `getSetCookie()` fallara en la versión de Bun instalada, el ejecutor debe reportarlo, no improvisar.

---

## 8. Pruebas:

*   **Pruebas Unitarias:** utils puros — firma/verificación JWT (roundtrip, expiración, firma adulterada, payload adulterado, tokens malformados, campos faltantes), construcción/parseo/expiración de cookies (strings exactos y casos borde), generación y hash de refresh tokens (vector sha256 conocido), hash/verificación argon2id, headers CORS y preflight.
*   **Pruebas de Integración:** flujos HTTP completos contra Postgres: login (éxito con cookies y JWT verificable, contraseña errónea, email inexistente, JSON inválido, validación zod, JWT_SECRET ausente → 500), refresh (éxito con rotación, token viejo muerto, cookie ausente, token basura), logout (con y sin sesión, idempotente, refresh posterior muere), fuerza bruta (flag off: 6 fallos no bloquean y el 7º correcto entra; flag on: 5 fallos bloquean; bloqueo expirado se resetea), CORS (preflight, origin no permitido, POST con/sin origin, 404 con CORS), y auditoría (línea JSON por evento, verificada por snapshot de conteo de líneas).
*   **Pruebas de Aceptación:** checklist de comandos del documento de instrucciones (sección "Verificación final"), incluida la demo negativa y la verificación de que `construerp_db` queda intacta.

---

## 9. Decisiones Tomadas:

*   **Sin `mock.module`:** evita contaminación entre archivos de test en un mismo proceso; el servicio se cubre por integración.
*   **Refactor `createServer`:** los tests de integración usan el routing real de producción (con `withCors`, preflight, 404 y 500) en lugar de duplicarlo.
*   **Env por preload (`bunfig.toml`)** en vez de `--env-file` o prefijos inline: un solo punto de configuración, antes de cualquier import de test.
*   **Filtro por sufijo de archivo** (`*.unit.test.ts` / `*.int.test.ts`): el filtro posicional de `bun test` matchea substrings de ruta; los sufijos son inmunes a separadores de Windows y mutuamente excluyentes.
*   **Auditoría por snapshot de líneas:** `auditLog` usa `appendFileSync` (síncrono), así que contar líneas antes/después de cada request es determinista; no se usa `process.chdir`.
*   **DB de test aprovisionada por script idempotente** ejecutado al inicio de `test:integration` (la migración usa `IF NOT EXISTS`).

---

## 10. Próximos Pasos:

*   Ejecutar [instrucciones_implementar_tests_login.md](instrucciones_implementar_tests_login.md) con el agente ejecutor.
*   Futuro: integrar la suite en CI, tests del frontend cuando exista, y migración `002` con expiración server-side del refresh token.
