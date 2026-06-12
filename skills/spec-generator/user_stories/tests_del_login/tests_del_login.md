# Historia de Usuario: Tests del Login

**ID de Historia:** HU-002
**Como...** Desarrollador
**Quiero...** Poder ejecutar tests automatizados (unitarios y de integración) del inicio de sesión
**Para...** Verificar que el login cumple su especificación, detectar regresiones antes de desplegar y poder refactorizar con confianza

---

## Criterios de Aceptación:

*   **ESCENARIO:** Ejecución de tests unitarios
    *   **DADO:** El repositorio clonado con Bun instalado y dependencias instaladas (`bun install`)
    *   **CUANDO:** El desarrollador ejecuta `bun run test:unit`
    *   **ENTONCES:** Todos los tests unitarios pasan en segundos, sin necesidad de Docker ni base de datos

*   **ESCENARIO:** Ejecución de tests de integración
    *   **DADO:** El contenedor Postgres de docker-compose está corriendo y healthy
    *   **CUANDO:** El desarrollador ejecuta `bun run test:integration`
    *   **ENTONCES:** Se aprovisiona automáticamente la base de datos de test `construerp_test` y pasan todos los escenarios del login contra el servidor HTTP real: login exitoso con emisión de cookies y tokens, rechazo 401 con mensaje genérico, 6 fallos consecutivos sin bloqueo (flag de fuerza bruta apagado), bloqueo tras 5 fallos (flag encendido), rotación de refresh token, logout, registro de auditoría y CORS

*   **ESCENARIO:** Aislamiento de la base de datos de desarrollo
    *   **DADO:** La base `construerp_db` contiene datos de desarrollo (usuario seed)
    *   **CUANDO:** Se ejecuta la suite completa de tests (`bun run test`)
    *   **ENTONCES:** Los datos de `construerp_db` quedan exactamente iguales; los tests solo escriben en `construerp_test`

*   **ESCENARIO:** Detección de regresiones
    *   **DADO:** Un cambio en el código que rompe el contrato del login (por ejemplo, cambiar el mensaje de error genérico)
    *   **CUANDO:** Se ejecuta la suite de tests
    *   **ENTONCES:** Al menos un test falla señalando el comportamiento roto

---

## Notas Adicionales:

*   Se usa `bun:test` (incluido en Bun): no se agregan dependencias nuevas.
*   No se usan mocks de módulos (`mock.module`): los utils se prueban como funciones puras y el resto del flujo se prueba de extremo a extremo contra Postgres real.
*   La base de test `construerp_test` vive en el mismo contenedor Postgres de docker-compose y se crea/migra automáticamente al correr `bun run test:integration`.
*   Depende de la HU "Inicio de Sesión de Usuario" (backend ya implementado).
*   Los tests cubren los criterios BDD definidos en `../inicio_de_sesion_de_usuario/plan_inicio_de_sesion_de_usuario.md`.

---

## Archivos Relacionados:

*   [plan_tests_del_login.md](plan_tests_del_login.md)
*   [instrucciones_implementar_tests_login.md](instrucciones_implementar_tests_login.md)
