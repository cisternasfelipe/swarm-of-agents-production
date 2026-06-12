# Instrucciones detalladas: terminar el login (backend)

---

## Contexto (para el agente ejecutor)

Repo: `C:\Users\felip\OneDrive\Documents\Documentos\Informatica\Proyectos\construerp-ia`. Backend en `backend/` con **Bun** (runtime), TypeScript, `Bun.serve` con la opción `routes` (sin Express/Hono) y PostgreSQL vía `Bun.sql` (`src/db.ts` re-exporta `sql` de `"bun"`). Dependencias: `argon2id`, `zod`. SO: Windows 11, shell PowerShell.

El login (`POST /api/auth/login`) ya está implementado con Argon2id, JWT + refresh token, auditoría y flag de fuerza bruta. Esta tarea lo **termina**:

1. **Corregir bug:** en `backend/src/controllers/authController.ts` los dos `Set-Cookie` se unen con coma (`.join(", ")`) — HTTP inválido; deben emitirse como dos headers separados con `Headers.append()`.
2. **Agregar `POST /api/auth/refresh`** con rotación de tokens (regla R2 de la spec) y **`POST /api/auth/logout`**.
3. **Agregar CORS** con credenciales para el futuro frontend (Next.js, tarea futura).
4. **Configurar entorno:** `docker-compose.yml` con Postgres, `.env`, scripts `migrate`/`seed` en `package.json`.

Alcance: **solo backend**. NO crear frontend. NO implementar registro ni recuperación de contraseña.

Regla general: donde este documento dice "contenido completo", **reemplaza el archivo entero** por el bloque de código dado. No improvises ni "mejores" el código; está alineado con el estilo existente.

---

## Paso 1 — Crear `docker-compose.yml` en la RAÍZ del repo (archivo nuevo)

Ruta exacta: `C:\Users\felip\OneDrive\Documents\Documentos\Informatica\Proyectos\construerp-ia\docker-compose.yml` (raíz, NO dentro de `backend/`).

Contenido completo:

```yaml
services:
  db:
    image: postgres:17-alpine
    container_name: construerp-db
    environment:
      POSTGRES_USER: construerp
      POSTGRES_PASSWORD: construerp_dev
      POSTGRES_DB: construerp_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U construerp -d construerp_db"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  pgdata:
```

## Paso 2 — Configuración: `.env.example`, `.env`, `.gitignore` (todos en `backend/`)

### 2a. `backend/.env.example` — contenido completo (se elimina `REFRESH_TOKEN_SECRET`, que no se usa en ninguna parte del código — los refresh tokens son valores aleatorios opacos hasheados con SHA-256, no JWTs; y se agrega `FRONTEND_ORIGIN`):

```
PORT=3000
DATABASE_URL=postgresql://construerp:construerp_dev@localhost:5432/construerp_db
JWT_SECRET=YOUR_VALUE
FEATURE_FLAG_BRUTE_FORCE=false
FRONTEND_ORIGIN=http://localhost:3001
SEED_USER_EMAIL=usuario@empresa.com
SEED_USER_PASSWORD=YOUR_SECURE_PASSWORD
```

### 2b. `backend/.env` — el archivo existe pero está VACÍO. Escribir este contenido, reemplazando `<SECRETO_GENERADO>` por el resultado de ejecutar (en `backend/`):

```powershell
bun -e "console.log(require('node:crypto').randomBytes(48).toString('hex'))"
```

Contenido (con el secreto ya sustituido):

```
PORT=3000
DATABASE_URL=postgresql://construerp:construerp_dev@localhost:5432/construerp_db
JWT_SECRET=<SECRETO_GENERADO>
FEATURE_FLAG_BRUTE_FORCE=false
FRONTEND_ORIGIN=http://localhost:3001
SEED_USER_EMAIL=usuario@empresa.com
SEED_USER_PASSWORD=Construerp#2026dev
```

Notas: Bun carga `.env` automáticamente desde el cwd y `Bun.sql` lee `DATABASE_URL` solo — no hace falta código de configuración. **Nunca commitear `.env`** (ya está en `.gitignore`).

### 2c. `backend/.gitignore` — contenido completo (hoy solo tiene `node_modules/` y `.env`; se agregan `logs/` porque los logs de auditoría contienen emails e IPs, y `cookies.txt` que se usa en la verificación):

```
node_modules/
.env
logs/
cookies.txt
```

## Paso 3 — Crear `backend/src/utils/cookies.ts` (archivo nuevo)

Centraliza construcción/parseo/expiración de cookies. **Decisión importante:** el Path del refresh cookie cambia de `/api/auth/refresh` a **`/api/auth`** — con el Path antiguo el navegador jamás enviaría la cookie a `/api/auth/logout`. Se mantiene `Secure` (los navegadores modernos y curl tratan `http://localhost` como contexto seguro).

Contenido completo:

```ts
export const ACCESS_COOKIE = "access_token";
export const REFRESH_COOKIE = "refresh_token";
export const ACCESS_MAX_AGE = 900;
export const REFRESH_MAX_AGE = 604800;
export const ACCESS_COOKIE_PATH = "/";
export const REFRESH_COOKIE_PATH = "/api/auth";

interface CookieOptions {
  httpOnly: boolean;
  secure: boolean;
  sameSite: string;
  path: string;
  maxAge: number;
}

export function buildCookie(name: string, value: string, options: CookieOptions): string {
  const parts = [`${name}=${value}`];
  parts.push(`Path=${options.path}`);
  parts.push(`Max-Age=${options.maxAge}`);
  if (options.httpOnly) parts.push("HttpOnly");
  if (options.secure) parts.push("Secure");
  parts.push(`SameSite=${options.sameSite}`);
  return parts.join("; ");
}

export function expireCookie(name: string, path: string): string {
  return [`${name}=`, `Path=${path}`, "Max-Age=0", "HttpOnly", "Secure", "SameSite=Lax"].join("; ");
}

export function parseCookies(header: string | null): Record<string, string> {
  const cookies: Record<string, string> = {};
  if (!header) return cookies;
  for (const part of header.split(";")) {
    const idx = part.indexOf("=");
    if (idx === -1) continue;
    const name = part.slice(0, idx).trim();
    let value = part.slice(idx + 1).trim();
    try {
      value = decodeURIComponent(value);
    } catch {
      // valor con encoding inválido: se conserva crudo
    }
    if (name) cookies[name] = value;
  }
  return cookies;
}
```

## Paso 4 — Crear `backend/src/utils/cors.ts` (archivo nuevo)

Como se usan cookies (credenciales), `Access-Control-Allow-Origin` debe ser el origin exacto (nunca `*`), controlado por la variable de entorno `FRONTEND_ORIGIN`.

Contenido completo:

```ts
type Handler = (req: Request) => Response | Promise<Response>;

export function appendCorsHeaders(headers: Headers, req: Request): void {
  const allowedOrigin = process.env.FRONTEND_ORIGIN;
  const origin = req.headers.get("Origin");
  if (allowedOrigin && origin === allowedOrigin) {
    headers.set("Access-Control-Allow-Origin", origin);
    headers.set("Access-Control-Allow-Credentials", "true");
    headers.set("Vary", "Origin");
  }
}

export function withCors(handler: Handler): Handler {
  return async (req: Request) => {
    const res = await handler(req);
    appendCorsHeaders(res.headers, req);
    return res;
  };
}

export function handlePreflight(req: Request): Response {
  const headers = new Headers();
  appendCorsHeaders(headers, req);
  headers.set("Access-Control-Allow-Methods", "POST, OPTIONS");
  headers.set("Access-Control-Allow-Headers", "Content-Type");
  headers.set("Access-Control-Max-Age", "86400");
  return new Response(null, { status: 204, headers });
}
```

Nota: en Bun los headers de un `Response` construido localmente son mutables. Si al compilar/ejecutar apareciera un error de "immutable headers" en `withCors`, reemplazar el cuerpo por: crear `const headers = new Headers(res.headers)`, hacer `appendCorsHeaders(headers, req)` y devolver `new Response(res.body, { status: res.status, headers })`.

## Paso 5 — Modificar `backend/src/repositories/userRepositories.ts`

NO tocar lo existente. **Agregar al final** estas dos funciones (el índice sobre `refresh_token_hash` ya existe en la migración 001):

```ts
export const getUserByRefreshTokenHash = async (
  refreshTokenHash: string
): Promise<User | null> => {
  const result = await sql<User[]>`
    SELECT id, email, password_hash, refresh_token_hash, failed_attempts, locked_until, created_at
    FROM users
    WHERE refresh_token_hash = ${refreshTokenHash}
    LIMIT 1
  `;
  return result[0] || null;
};

export const clearRefreshToken = async (userId: string): Promise<void> => {
  await sql`UPDATE users SET refresh_token_hash = NULL WHERE id = ${userId}`;
};
```

## Paso 6 — Reemplazar `backend/src/services/authService.ts` (contenido completo)

Cambios respecto al actual: se extrae el helper `issueTokens` (antes inline en `loginUser`), se agregan `refreshSession` y `logoutUser`, y se agrega el helper `requireJwtSecret`. La lógica de `loginUser` (fuerza bruta, auditoría, mensaje genérico) queda **idéntica**.

```ts
import {
  getUserByEmail,
  getUserByRefreshTokenHash,
  updateRefreshTokenHash,
  clearRefreshToken,
  incrementFailedAttempts,
  resetFailedAttempts,
  lockUser,
} from "../repositories/userRepositories";
import type { User } from "../repositories/userRepositories";
import { verifyPassword } from "../utils/auth";
import { hashRefreshToken, generateRefreshToken } from "../utils/authToken";
import { signJwt } from "../utils/jwt";
import { auditLog } from "../utils/logger";

interface LoginInput {
  email: string;
  password: string;
  ip: string;
}

interface RefreshInput {
  refreshToken: string;
  ip: string;
}

interface LogoutInput {
  refreshToken: string | null;
  ip: string;
}

interface LoginResult {
  accessToken: string;
  refreshToken: string;
}

type LoginError = {
  type: "INVALID_CREDENTIALS";
  message: string;
};

type RefreshError = {
  type: "INVALID_REFRESH_TOKEN";
};

const GENERIC_ERROR_MESSAGE = "Correo electrónico o contraseña incorrectos";
const ACCESS_TOKEN_TTL_SECONDS = 900;

const buildInvalidCredentials = (): LoginError => ({
  type: "INVALID_CREDENTIALS",
  message: GENERIC_ERROR_MESSAGE,
});

function requireJwtSecret(): string {
  const jwtSecret = process.env.JWT_SECRET;
  if (!jwtSecret) {
    throw new Error("JWT_SECRET not configured");
  }
  return jwtSecret;
}

async function issueTokens(user: User, jwtSecret: string): Promise<LoginResult> {
  const accessToken = signJwt(
    { userId: user.id, email: user.email },
    jwtSecret,
    ACCESS_TOKEN_TTL_SECONDS
  );

  const refreshToken = generateRefreshToken();
  const refreshTokenHash = hashRefreshToken(refreshToken);
  await updateRefreshTokenHash(user.id, refreshTokenHash);

  return { accessToken, refreshToken };
}

export async function loginUser(input: LoginInput): Promise<LoginResult | LoginError> {
  const jwtSecret = requireJwtSecret();

  const bruteForceEnabled = process.env.FEATURE_FLAG_BRUTE_FORCE === "true";

  const user = await getUserByEmail(input.email);

  if (!user) {
    auditLog({
      event: "LOGIN_FAILURE",
      email: input.email,
      ip: input.ip,
      result: "user_not_found",
    });
    return buildInvalidCredentials();
  }

  if (bruteForceEnabled && user.locked_until !== null && user.locked_until > new Date()) {
    auditLog({
      event: "LOGIN_FAILURE",
      email: user.email,
      ip: input.ip,
      result: "account_locked",
    });
    return buildInvalidCredentials();
  }

  const isPasswordValid = await verifyPassword(input.password, user.password_hash);

  if (!isPasswordValid) {
    auditLog({
      event: "LOGIN_FAILURE",
      email: user.email,
      ip: input.ip,
      result: "invalid_password",
    });

    if (bruteForceEnabled) {
      await incrementFailedAttempts(user.id);
      if (user.failed_attempts + 1 >= 5) {
        await lockUser(user.id, new Date(Date.now() + 15 * 60 * 1000));
      }
    }

    return buildInvalidCredentials();
  }

  if (bruteForceEnabled) {
    await resetFailedAttempts(user.id);
  }

  const tokens = await issueTokens(user, jwtSecret);

  auditLog({
    event: "LOGIN_SUCCESS",
    email: user.email,
    ip: input.ip,
    result: "success",
  });

  return tokens;
}

export async function refreshSession(input: RefreshInput): Promise<LoginResult | RefreshError> {
  const jwtSecret = requireJwtSecret();

  const refreshTokenHash = hashRefreshToken(input.refreshToken);
  const user = await getUserByRefreshTokenHash(refreshTokenHash);

  if (!user) {
    auditLog({
      event: "REFRESH_FAILURE",
      email: "unknown",
      ip: input.ip,
      result: "token_not_found",
    });
    return { type: "INVALID_REFRESH_TOKEN" };
  }

  const tokens = await issueTokens(user, jwtSecret);

  auditLog({
    event: "REFRESH_SUCCESS",
    email: user.email,
    ip: input.ip,
    result: "success",
  });

  return tokens;
}

export async function logoutUser(input: LogoutInput): Promise<void> {
  if (input.refreshToken) {
    const refreshTokenHash = hashRefreshToken(input.refreshToken);
    const user = await getUserByRefreshTokenHash(refreshTokenHash);

    if (user) {
      await clearRefreshToken(user.id);
      auditLog({
        event: "LOGOUT",
        email: user.email,
        ip: input.ip,
        result: "success",
      });
      return;
    }
  }

  auditLog({
    event: "LOGOUT",
    email: "unknown",
    ip: input.ip,
    result: "no_session",
  });
}

export type { LoginInput, LoginResult, LoginError, RefreshError };
```

Notas: la rotación funciona porque `issueTokens` sobrescribe `refresh_token_hash` — el token anterior muere al instante. `logoutUser` es idempotente y nunca lanza error por sesión inexistente. `auditLog` acepta cualquier `event: string`, no hay que tocar `logger.ts`.

## Paso 7 — Reemplazar `backend/src/controllers/authController.ts` (contenido completo)

Cambios: fix del bug `Set-Cookie` (ahora `Headers.append()`, dos headers separados), nuevos handlers `handleRefresh` y `handleLogout`, helpers `getClientIp` / `problemJson` / `buildSessionHeaders`, cookies importadas desde `utils/cookies.ts`, y el refresh cookie ahora con `Path=/api/auth`.

```ts
import { z } from "zod";
import { loginUser, refreshSession, logoutUser } from "../services/authService";
import type { LoginError } from "../services/authService";
import { auditLog } from "../utils/logger";
import {
  buildCookie,
  expireCookie,
  parseCookies,
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  ACCESS_MAX_AGE,
  REFRESH_MAX_AGE,
  ACCESS_COOKIE_PATH,
  REFRESH_COOKIE_PATH,
} from "../utils/cookies";

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

function isLoginError(result: unknown): result is LoginError {
  return (
    typeof result === "object" &&
    result !== null &&
    "type" in result &&
    (result as LoginError).type === "INVALID_CREDENTIALS"
  );
}

function getClientIp(req: Request): string {
  return req.headers.get("x-forwarded-for")?.split(",")[0].trim() ?? "unknown";
}

function problemJson(
  status: number,
  title: string,
  detail: string,
  extra?: Record<string, unknown>
): Response {
  return Response.json(
    { type: "about:blank", title, status, detail, ...extra },
    { status, headers: { "Content-Type": "application/problem+json" } }
  );
}

function buildSessionHeaders(accessToken: string, refreshToken: string): Headers {
  const accessCookie = buildCookie(ACCESS_COOKIE, accessToken, {
    httpOnly: true,
    secure: true,
    sameSite: "Lax",
    path: ACCESS_COOKIE_PATH,
    maxAge: ACCESS_MAX_AGE,
  });

  const refreshCookie = buildCookie(REFRESH_COOKIE, refreshToken, {
    httpOnly: true,
    secure: true,
    sameSite: "Lax",
    path: REFRESH_COOKIE_PATH,
    maxAge: REFRESH_MAX_AGE,
  });

  const headers = new Headers({ "Content-Type": "application/json" });
  headers.append("Set-Cookie", accessCookie);
  headers.append("Set-Cookie", refreshCookie);
  return headers;
}

export async function handleLogin(req: Request): Promise<Response> {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return problemJson(400, "Bad Request", "Invalid JSON body");
  }

  const validation = loginSchema.safeParse(body);
  if (!validation.success) {
    return problemJson(400, "Bad Request", "Validation failed", {
      errors: validation.error.issues,
    });
  }

  const { email, password } = validation.data;
  const result = await loginUser({ email, password, ip: getClientIp(req) });

  if (isLoginError(result)) {
    return problemJson(401, "Unauthorized", "Correo electrónico o contraseña incorrectos");
  }

  return new Response(JSON.stringify({ message: "Login exitoso" }), {
    status: 200,
    headers: buildSessionHeaders(result.accessToken, result.refreshToken),
  });
}

export async function handleRefresh(req: Request): Promise<Response> {
  const ip = getClientIp(req);
  const cookies = parseCookies(req.headers.get("Cookie"));
  const refreshToken = cookies[REFRESH_COOKIE];

  if (!refreshToken) {
    auditLog({
      event: "REFRESH_FAILURE",
      email: "unknown",
      ip,
      result: "missing_cookie",
    });
    return problemJson(401, "Unauthorized", "Sesión inválida o expirada");
  }

  const result = await refreshSession({ refreshToken, ip });

  if ("type" in result) {
    return problemJson(401, "Unauthorized", "Sesión inválida o expirada");
  }

  return new Response(JSON.stringify({ message: "Sesión renovada" }), {
    status: 200,
    headers: buildSessionHeaders(result.accessToken, result.refreshToken),
  });
}

export async function handleLogout(req: Request): Promise<Response> {
  const ip = getClientIp(req);
  const cookies = parseCookies(req.headers.get("Cookie"));
  const refreshToken = cookies[REFRESH_COOKIE] ?? null;

  await logoutUser({ refreshToken, ip });

  const headers = new Headers({ "Content-Type": "application/json" });
  headers.append("Set-Cookie", expireCookie(ACCESS_COOKIE, ACCESS_COOKIE_PATH));
  headers.append("Set-Cookie", expireCookie(REFRESH_COOKIE, REFRESH_COOKIE_PATH));

  return new Response(JSON.stringify({ message: "Sesión cerrada" }), {
    status: 200,
    headers,
  });
}
```

## Paso 8 — Reemplazar `backend/src/index.ts` (contenido completo)

**Gotcha del router de Bun:** una ruta que solo define `POST` responde 405 automático a cualquier otro método, así que el preflight `OPTIONS` debe declararse explícitamente en CADA ruta (no sirve un wildcard).

```ts
import { handleLogin, handleRefresh, handleLogout } from "./controllers/authController";
import { withCors, handlePreflight, appendCorsHeaders } from "./utils/cors";

const port = Number(process.env.PORT) || 3000;

Bun.serve({
  port,
  routes: {
    "/api/auth/login": {
      POST: withCors(handleLogin),
      OPTIONS: handlePreflight,
    },
    "/api/auth/refresh": {
      POST: withCors(handleRefresh),
      OPTIONS: handlePreflight,
    },
    "/api/auth/logout": {
      POST: withCors(handleLogout),
      OPTIONS: handlePreflight,
    },
  },
  fetch(req) {
    const headers = new Headers({ "Content-Type": "application/problem+json" });
    appendCorsHeaders(headers, req);
    return new Response(
      JSON.stringify({
        type: "about:blank",
        title: "Not Found",
        status: 404,
        detail: "Ruta no encontrada",
      }),
      { status: 404, headers }
    );
  },
  error(error) {
    console.error("Server error:", error);
    return Response.json(
      {
        type: "about:blank",
        title: "Internal Server Error",
        status: 500,
        detail: "Error interno del servidor",
      },
      {
        status: 500,
        headers: { "Content-Type": "application/problem+json" },
      }
    );
  },
});

console.log(`Server running on http://localhost:${port}`);
```

## Paso 9 — Scripts: `package.json`, `migrate.ts`, `seed.ts`

### 9a. `backend/package.json` — reemplazar solo el bloque `"scripts"` por:

```json
"scripts": {
  "dev": "bun --watch src/index.ts",
  "start": "bun src/index.ts",
  "migrate": "bun run scripts/migrate.ts",
  "seed": "bun run scripts/seed.ts"
}
```

### 9b. `backend/scripts/migrate.ts` — contenido completo (fix: la ruta actual es relativa al cwd y rompe si se ejecuta desde la raíz; además el pool de Bun.sql deja el proceso colgado sin `process.exit`):

```ts
import { join } from "node:path";
import { sql } from "../src/db";

await sql.file(join(import.meta.dir, "..", "migrations", "001_create_users_table.sql"));
console.log("Migración completada exitosamente.");
process.exit(0);
```

### 9c. `backend/scripts/seed.ts` — contenido completo (único cambio: `process.exit(0)` al final):

```ts
import { sql } from "../src/db";
import { hashPassword } from "../src/utils/auth";

const email = process.env.SEED_USER_EMAIL;
const password = process.env.SEED_USER_PASSWORD;

if (!email || !password) {
  throw new Error("SEED_USER_EMAIL o SEED_USER_PASSWORD no están definidas.");
}

const passwordHash = await hashPassword(password);

await sql`
  INSERT INTO users (email, password_hash)
  VALUES (${email}, ${passwordHash})
  ON CONFLICT (email) DO NOTHING;
`;
console.log("Usuario de prueba seed exitoso.");
process.exit(0);
```

## Paso 10 — Archivos que NO se tocan

`src/db.ts`, `src/utils/auth.ts`, `src/utils/jwt.ts`, `src/utils/authToken.ts`, `src/utils/logger.ts`, `migrations/001_create_users_table.sql`. Si crees que necesitan cambios, detente y pregunta al usuario.

---

## Verificación end-to-end

⚠️ En PowerShell usar **`curl.exe`** (el alias `curl` es Invoke-WebRequest y no sirve para esto). Los comandos con JSON usan comillas escapadas `\"` dentro de comillas simples — copiarlos tal cual.

### Arranque

Desde la raíz del repo:

```powershell
docker compose up -d
docker compose ps
```

Esperar a que `construerp-db` aparezca `healthy` (reintenta `docker compose ps` unos segundos si hace falta). Luego, desde `backend/`:

```powershell
bun install
bun run migrate    # espera: "Migración completada exitosamente."
bun run seed       # espera: "Usuario de prueba seed exitoso."
bun run dev        # dejar corriendo (terminal aparte o proceso en background)
```

Si `bun run migrate` fallara con error de multi-statement, fallback: `docker exec -i construerp-db psql -U construerp -d construerp_db < backend\migrations\001_create_users_table.sql` (desde la raíz).

### Pruebas (desde `backend/`)

**1. Login exitoso → 200 con DOS headers `Set-Cookie`:**

```powershell
curl.exe -i -s -c cookies.txt -X POST http://localhost:3000/api/auth/login -H "Content-Type: application/json" -d '{\"email\":\"usuario@empresa.com\",\"password\":\"Construerp#2026dev\"}'
```

Verificar: status 200; UNA línea `Set-Cookie: access_token=...; Path=/; Max-Age=900; HttpOnly; Secure; SameSite=Lax` y OTRA línea `Set-Cookie: refresh_token=...; Path=/api/auth; Max-Age=604800; HttpOnly; Secure; SameSite=Lax`. Si vienen unidas en una sola línea con coma, el fix del Paso 7 no se aplicó.

**2. Login inválido → 401 genérico:**

```powershell
curl.exe -i -s -X POST http://localhost:3000/api/auth/login -H "Content-Type: application/json" -d '{\"email\":\"usuario@empresa.com\",\"password\":\"wrong\"}'
```

Verificar: status 401 y `detail` EXACTAMENTE `"Correo electrónico o contraseña incorrectos"` (mismo mensaje exista o no el usuario — regla R4).

**3. Seis fallos seguidos NO bloquean (flag de fuerza bruta apagado — criterio de aceptación R5):**

```powershell
1..6 | ForEach-Object { curl.exe -s -o NUL -w "%{http_code}`n" -X POST http://localhost:3000/api/auth/login -H "Content-Type: application/json" -d '{\"email\":\"usuario@empresa.com\",\"password\":\"wrong\"}' }
docker exec construerp-db psql -U construerp -d construerp_db -c "SELECT failed_attempts, locked_until FROM users;"
```

Verificar: seis `401`; en la DB `failed_attempts = 0` y `locked_until = NULL`; y repetir el comando del punto 1 → sigue dando 200 (séptimo intento permitido).

**4. Rotación de refresh token:**

```powershell
$old = ((Get-Content cookies.txt | Select-String "refresh_token") -split "\s+")[-1]
curl.exe -i -s -b cookies.txt -c cookies.txt -X POST http://localhost:3000/api/auth/refresh
curl.exe -i -s -X POST http://localhost:3000/api/auth/refresh -H "Cookie: refresh_token=$old"
```

Verificar: el primer refresh → 200 con dos `Set-Cookie` nuevos; el segundo (replay del token viejo) → 401 con detail `"Sesión inválida o expirada"`.

**5. Logout:**

```powershell
curl.exe -i -s -b cookies.txt -X POST http://localhost:3000/api/auth/logout
docker exec construerp-db psql -U construerp -d construerp_db -c "SELECT refresh_token_hash FROM users;"
curl.exe -i -s -b cookies.txt -X POST http://localhost:3000/api/auth/refresh
```

Verificar: logout → 200 con ambos `Set-Cookie` en `Max-Age=0`; en DB `refresh_token_hash` es NULL; el refresh posterior → 401.

**6. CORS preflight:**

```powershell
curl.exe -i -s -X OPTIONS http://localhost:3000/api/auth/login -H "Origin: http://localhost:3001" -H "Access-Control-Request-Method: POST"
```

Verificar: 204 con `Access-Control-Allow-Origin: http://localhost:3001`, `Access-Control-Allow-Credentials: true`, `Access-Control-Allow-Methods: POST, OPTIONS`.

**7. Auditoría:** abrir `backend\logs\audit-<fecha-de-hoy>.log` y verificar que hay líneas JSON con eventos `LOGIN_SUCCESS`, `LOGIN_FAILURE` (x7+), `REFRESH_SUCCESS`, `REFRESH_FAILURE`, `LOGOUT`, cada una con `timestamp`, `email`, `ip`, `result`.

**8. Limpieza:** borrar `cookies.txt`. No commitear `.env`, `logs/` ni `cookies.txt` (el `.gitignore` del Paso 2c los cubre).

### Checklist de finalización

- [ ] `docker-compose.yml` creado y Postgres `healthy`
- [ ] `.env`, `.env.example`, `.gitignore` actualizados
- [ ] `cookies.ts` y `cors.ts` creados
- [ ] `userRepositories.ts` con las 2 funciones nuevas
- [ ] `authService.ts` y `authController.ts` reemplazados
- [ ] `index.ts` con 3 rutas + OPTIONS
- [ ] `package.json`, `migrate.ts`, `seed.ts` actualizados
- [ ] Las 7 verificaciones pasan
- [ ] `bun run dev` arranca sin errores de TypeScript

---

## Riesgos conocidos (documentar, NO arreglar ahora)

- **Sin expiración server-side del refresh token** (solo el `Max-Age` de la cookie). Una futura migración `002` podría agregar `refresh_token_expires_at`. La spec (R2) solo exige rotación — cumplido.
- **Un solo slot de refresh por usuario:** iniciar sesión en un segundo dispositivo invalida la sesión del primero (una sola columna `refresh_token_hash`).
- **Oráculo de timing en login:** cuando el email no existe se salta el verify de Argon2id (respuesta más rápida). Hardening futuro opcional: verificar contra un hash dummy.
- **`REFRESH_TOKEN_SECRET` eliminado de `.env.example`:** se confirmó que ningún código lo usa.
