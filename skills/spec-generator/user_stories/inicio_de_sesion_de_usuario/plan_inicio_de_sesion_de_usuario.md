# Plan de Implementación: Inicio de Sesión de Usuario

## 9. Reglas de negocio

*   **R1 - Criptografía (ISO 27001 Anexo A):** Prohibido almacenar o transmitir contraseñas en texto plano. Las validaciones criptográficas deben usar estándares modernos como Argon2id o bcrypt (work factor alto).
*   **R2 - Gestión de Sesión:** La sesión debe manejarse mediante JWT de corta duración y rotación de Refresh Tokens. No se expondrán tokens sensibles en el LocalStorage de React.
*   **R3 - Auditoría Inquebrantable (CIS):** Todo intento de inicio de sesión, sin importar si es exitoso o fallido, debe generar un log de trazabilidad con la fecha/hora, IP de origen (si las políticas de privacidad lo permiten) y el resultado de la operación.
*   **R4 - Opacidad ante Errores:** Por seguridad (evitar enumeración de usuarios), la interfaz jamás debe indicar si lo que falló fue el correo o la contraseña, usando un único mensaje de error genérico unificado.
*   **R5 - Prevención de Fuerza Bruta (Flag-Controlled):** El código fuente en Node.js DEBE contar con la lógica necesaria para bloquear intentos de inicio de sesión durante 15 minutos tras 5 intentos fallidos consecutivos por cuenta/IP. Sin embargo, esta lógica estará envuelta en un condicional controlado por configuración (ej. FEATURE_FLAG_BRUTE_FORCE = false), de manera que la restricción se encuentre actualmente deshabilitada en la ejecución hasta su activación futura.

## 10. Criterios de aceptación

*   Un usuario con credenciales correctas logra acceder al sistema y se le emiten sus tokens correspondientes de forma segura.
*   Un usuario con credenciales incorrectas (cualquiera de ellas) es rechazado y recibe siempre el mismo mensaje de error genérico en la pantalla de React.
*   Si un usuario se equivoca 6 veces seguidas, el sistema le permite el 7mo intento sin bloqueo, demostrando que la regla R5 (Prevención de Fuerza Bruta) está efectivamente controlada y apagada por el feature flag en esta etapa.
*   Revisando la consola del servidor o el archivo de registros de Node.js, se evidencia un registro de auditoría estructurado por cada intento de inicio de sesión.

## 11. Resultado esperado

El usuario puede ingresar a su cuenta, el sistema gestiona la sesión protegiendo la identidad con estándares empresariales de criptografía y trazabilidad, y la infraestructura de código queda preparada (aunque silenciada temporalmente) para repeler ataques automatizados.

## 12. BDD (Behavior-Driven Development)

### Feature: Autenticación Segura de Usuario

#### Scenario: Inicio de sesión exitoso con registro de auditoría
*   **Given** que el usuario "usuario@empresa.com" tiene una cuenta activa y válida
*   **And** el sistema de auditoría está en funcionamiento
*   **When** el usuario ingresa su correo "usuario@empresa.com" y su contraseña correcta
*   **And** presiona el botón "Iniciar Sesión"
*   **Then** el backend valida las credenciales y devuelve tokens de sesión seguros
*   **And** el backend registra un evento de "Login Exitoso" en el sistema de logs
*   **And** el frontend redirige al usuario al panel de control

#### Scenario: Intento de inicio de sesión con credenciales inválidas (Mensaje Genérico)
*   **Given** que el usuario se encuentra en la pantalla de inicio de sesión
*   **When** el usuario ingresa una contraseña incorrecta para cualquier correo electrónico
*   **And** presiona el botón "Iniciar Sesión"
*   **Then** el backend rechaza la solicitud
*   **And** el backend registra un evento de "Fallo de Autenticación" en el sistema de logs
*   **And** el frontend muestra el mensaje de error unificado: "Correo electrónico o contraseña incorrectos"
*   **And** el usuario permanece en la pantalla de inicio de sesión

#### Scenario: Protección contra fuerza bruta deshabilitada mediante flag
*   **Given** que el sistema tiene el control de fuerza bruta configurado con el flag "false"
*   **And** un atacante intenta iniciar sesión con la misma cuenta
*   **When** el atacante ingresa credenciales incorrectas 6 veces consecutivas
*   **Then** el sistema registra cada fallo de autenticación de forma independiente en los logs
*   **And** el sistema NO bloquea la cuenta tras el 5to intento
*   **And** el sistema permite un 7mo intento de validación contra la base de datos
