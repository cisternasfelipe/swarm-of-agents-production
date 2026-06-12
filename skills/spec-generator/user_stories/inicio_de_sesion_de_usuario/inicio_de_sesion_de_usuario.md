# Especificación de Software: Inicio de Sesión de Usuario

## 1. Historia de usuario

Como usuario quiero poder iniciar sesion.

## 2. Objetivo

Proveer un mecanismo seguro y robusto para que los usuarios registrados puedan autenticarse en la aplicación y acceder a sus recursos, garantizando que el flujo de autenticación (React + Node.js) cumpla con políticas de ciberseguridad basadas en controles CIS y la norma ISO 27001:2022.

## 3. Alcance

Esta especificación abarca la captura de credenciales (correo y contraseña) en la interfaz de usuario (React), su transmisión segura, la validación contra la base de datos en el backend (Node.js) mediante algoritmos criptográficos fuertes, la generación y entrega de tokens de sesión (JWT y Refresh Tokens), el registro en logs de auditoría y la codificación de un mecanismo de mitigación de ataques de fuerza bruta (actualmente inactivo mediante flag). No incluye en este momento los flujos de "Recuperación de contraseña" o "Registro de nuevo usuario".

## 4. Actores

*   **Usuario:** Persona que interactúa con la interfaz (Frontend) para acceder a su cuenta.
*   **Sistema Frontend (React):** Capa de presentación que captura, envía las credenciales y maneja la sesión localmente.
*   **Sistema Backend (Node.js):** Capa lógica que procesa la validación, aplica políticas de seguridad, maneja la criptografía y los logs de auditoría.
*   **Base de Datos:** Repositorio que almacena la información del usuario y los hashes de sus contraseñas.

## 5. Precondiciones

*   El usuario debe poseer una cuenta previamente registrada en el sistema.
*   La contraseña almacenada en la base de datos debe estar hasheada cumpliendo con políticas de complejidad y entropía (controles CIS).
*   El entorno de ejecución debe estar operando bajo un canal seguro (TLS 1.2 o superior).

## 6. Disparador

El usuario presiona el botón de "Iniciar Sesión" (o envía el formulario con la tecla Enter) después de haber ingresado su correo electrónico y su contraseña en los campos correspondientes.

## 7. Flujo Principal

1.  El Usuario introduce su correo electrónico y contraseña en el formulario de inicio de sesión en React.
2.  El Sistema Frontend valida a nivel local que ambos campos no estén vacíos y tengan el formato correcto (ej. el correo incluye un "@").
3.  El Sistema Frontend envía una petición segura (POST) al Sistema Backend con las credenciales ingresadas.
4.  El Sistema Backend intercepta la petición y valida la estructura de los datos de entrada.
5.  El Sistema Backend busca al usuario en la Base de Datos utilizando el correo electrónico proporcionado.
6.  Al encontrar el registro, el Sistema Backend compara la contraseña recibida con el hash almacenado utilizando un algoritmo robusto (ej. Argon2 o bcrypt).
7.  La validación es exitosa (la contraseña coincide).
8.  El Sistema Backend genera un evento de éxito y lo almacena en el sistema de logs centralizado para auditoría.
9.  El Sistema Backend crea un JWT cifrado de vida corta y un Refresh Token (siguiendo prácticas de gestión de identidad de ISO 27001).
10. El Sistema Backend responde al Sistema Frontend inyectando los tokens (preferiblemente en cookies HTTP-only para prevenir XSS).
11. El Sistema Frontend redirige al usuario a la pantalla principal o panel de control (Dashboard).

## 8. Flujos Alternativos

### FA1 - Credenciales Inválidas (Usuario no existe o contraseña incorrecta):

*   En el paso 5 o 6 del flujo principal, la validación falla.
*   El Sistema Backend registra un evento de fallo de autenticación en los logs de auditoría.
*   El Sistema Backend devuelve un error HTTP 401 al Frontend.
*   El Sistema Frontend muestra el mensaje genérico: "Correo electrónico o contraseña incorrectos". El flujo finaliza.

### FA2 - Sistema de Backend no disponible o error de red:

*   En el paso 3 del flujo principal, el Frontend no logra establecer conexión con el Backend.
*   El Sistema Frontend captura la excepción (Timeout o Error 500+).
*   El Sistema Frontend muestra un mensaje: "Servicio no disponible temporalmente. Por favor, intente más tarde."

---

## Archivos Relacionados:

*   [plan_inicio_de_sesion_de_usuario.md](plan_inicio_de_sesion_de_usuario.md)
