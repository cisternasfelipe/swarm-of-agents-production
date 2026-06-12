# Instrucciones detalladas: implementar tests del login (HU-002)

## Contexto (para el agente ejecutor)

Repo: `C:\Users\felip\OneDrive\Documents\Documentos\Informatica\Proyectos\construerp-ia`. Backend en `backend/`: Bun + TypeScript estricto, `Bun.serve` con `routes`, PostgreSQL vía `Bun.sql`. El login ya está implementado (`POST /api/auth/login`, `/refresh`, `/logout`). Esta tarea agrega la suite de tests de la HU-002. SO: Windows 11, PowerShell.

Reglas estrictas:
1. Donde diga "contenido completo", **reemplaza o crea el archivo entero** con el bloque dado. No improvises ni "mejores" el código.
2. **PROHIBIDO usar `mock.module`** de bun:test en cualquier archivo.
3. **PROHIBIDO apuntar `DATABASE_URL` a `construerp_db`** en cualquier archivo de test.
4. Varios strings asertados contienen acentos (`"Correo electrónico o contraseña incorrectos"`, `"Sesión inválida o expirada"`...). Escribe los archivos en **UTF-8** (usa la herramienta Write/Edit, nunca `Out-File` de PowerShell sin `-Encoding utf8`). Las aserciones son byte-exactas.
5. Si algo falla de forma distinta a lo previsto en "Riesgos residuales", detente y reporta; no inventes soluciones.

Estructura final que vas a crear:

```
backend/
  bunfig.toml                          (NUEVO)
  tests/
    preload.ts                         (NUEVO)
    helpers/
      constants.ts                     (NUEVO)
    unit/
      jwt.unit.test.ts                 (NUEVO)
      cookies.unit.test.ts             (NUEVO)
      authToken.unit.test.ts           (NUEVO)
      auth.unit.test.ts                (NUEVO)
      cors.unit.test.ts                (NUEVO)
    integration/
      helpers/
        db.ts                          (NUEVO)
        fixtures.ts                    (NUEVO)
        server.ts                      (NUEVO)
        http.ts                        (NUEVO)
        audit.ts                       (NUEVO)
      login.int.test.ts                (NUEVO)
      refresh.int.test.ts              (NUEVO)
      logout.int.test.ts               (NUEVO)
      bruteforce.int.test.ts           (NUEVO)
      cors.int.test.ts                 (NUEVO)
  scripts/
    setup-test-db.ts                   (NUEVO)
  src/
    server.ts                          (NUEVO)
    index.ts                           (REEMPLAZAR)
  tsconfig.json                        (MODIFICAR include)
  package.json                         (MODIFICAR scripts)
```

---

## Paso 0 — Pre-flight

Desde la raíz del repo:

```powershell
docker compose up -d
docker inspect -f "{{.State.Health.Status}}" construerp-db
```

Repite el `docker inspect` hasta que imprima `healthy`. Todos los comandos siguientes se ejecutan desde `backend/`.

```powershell
bun install
```

---

## Paso 1 — Configuración de test: `bunfig.toml`, constantes y preload

### 1a. Crear `backend/bunfig.toml` (contenido completo):

```toml
[test]
preload = ["./tests/preload.ts"]
```

### 1b. Crear `backend/tests/helpers/constants.ts` (contenido completo):

```ts
export const TEST_DB_NAME = "construerp_test";
export const ADMIN_DATABASE_URL =
  "postgresql://construerp:construerp_dev@localhost:5432/postgres";
export const TEST_DATABASE_URL = `postgresql://construerp:construerp_dev@localhost:5432/${TEST_DB_NAME}`;
export const TEST_JWT_SECRET =
  "construerp-test-secret-0123456789abcdef0123456789abcdef";
export const TEST_FRONTEND_ORIGIN = "http://localhost:3001";
```

### 1c. Crear `backend/tests/preload.ts` (contenido completo). Se ejecuta antes de importar cualquier archivo de test y pisa el `.env` auto-cargado:

```ts
import {
  TEST_DATABASE_URL,
  TEST_JWT_SECRET,
  TEST_FRONTEND_ORIGIN,
} from "./helpers/constants";

process.env.DATABASE_URL = TEST_DATABASE_URL;
process.env.JWT_SECRET = TEST_JWT_SECRET;
process.env.FEATURE_FLAG_BRUTE_FORCE = "false";
process.env.FRONTEND_ORIGIN = TEST_FRONTEND_ORIGIN;
```

---

## Paso 2 — Refactor mínimo de producción: `src/server.ts` + `src/index.ts`

Los tests necesitan levantar el servidor real en proceso con puerto efímero. Se extrae la creación del servidor a una factory. **El comportamiento de producción no cambia.**

### 2a. Crear `backend/src/server.ts` (contenido completo — los cuerpos vienen del `index.ts` actual sin cambios):

```ts
import { handleLogin, handleRefresh, handleLogout } from "./controllers/authController";
import { withCors, handlePreflight, appendCorsHeaders } from "./utils/cors";

export function createServer(port: number) {
  return Bun.serve({
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
}
```

### 2b. Reemplazar `backend/src/index.ts` (contenido completo):

```ts
import { createServer } from "./server";

const port = Number(process.env.PORT) || 3000;
const server = createServer(port);

console.log(`Server running on http://localhost:${server.port}`);
```

### 2c. Smoke check: `bun run start` debe imprimir `Server running on http://localhost:3000`. Detenerlo con Ctrl+C (o matando el proceso) antes de seguir.

---

## Paso 3 — Aprovisionamiento de la DB de test: `scripts/setup-test-db.ts`

Crear `backend/scripts/setup-test-db.ts` (contenido completo). Usa conexiones explícitas `new SQL(...)` (ignora el `.env`), crea `construerp_test` si no existe y aplica la migración (idempotente: usa `IF NOT EXISTS`):

```ts
import { SQL } from "bun";
import { join } from "node:path";
import {
  TEST_DB_NAME,
  TEST_DATABASE_URL,
  ADMIN_DATABASE_URL,
} from "../tests/helpers/constants";

const admin = new SQL(ADMIN_DATABASE_URL);
const rows = await admin`SELECT 1 FROM pg_database WHERE datname = ${TEST_DB_NAME}`;
if (rows.length === 0) {
  await admin.unsafe(`CREATE DATABASE ${TEST_DB_NAME}`);
  console.log(`Base de datos ${TEST_DB_NAME} creada.`);
}
await admin.close();

const testDb = new SQL(TEST_DATABASE_URL);
const migration = await Bun.file(
  join(import.meta.dir, "..", "migrations", "001_create_users_table.sql")
).text();
await testDb.unsafe(migration);
await testDb.close();
console.log(`Migración aplicada a ${TEST_DB_NAME}.`);
process.exit(0);
```

Probar: `bun run scripts/setup-test-db.ts` → debe terminar con `Migración aplicada a construerp_test.` (la primera vez también imprime que creó la base). Ejecutarlo dos veces: la segunda también debe salir exitosa.

---

## Paso 4 — `tsconfig.json` y `package.json`

### 4a. En `backend/tsconfig.json`, cambiar la línea de `include` de `["src/**/*"]` a:

```json
"include": ["src/**/*", "tests/**/*", "scripts/**/*"]
```

### 4b. En `backend/package.json`, reemplazar el bloque `"scripts"` completo por:

```json
"scripts": {
  "dev": "bun --watch src/index.ts",
  "start": "bun src/index.ts",
  "migrate": "bun run scripts/migrate.ts",
  "seed": "bun run scripts/seed.ts",
  "test": "bun run test:unit && bun run test:integration",
  "test:unit": "bun test --timeout 15000 unit.test",
  "test:setup-db": "bun run scripts/setup-test-db.ts",
  "test:integration": "bun run test:setup-db && bun test --timeout 30000 int.test"
}
```

Notas: `bun test <filtro>` matchea por substring de ruta; los sufijos `unit.test` / `int.test` son mutuamente excluyentes y funcionan igual en Windows. Los scripts corren con el shell de Bun, así que `&&` es multiplataforma. `test` ejecuta las dos suites en **procesos separados**.

---

## Paso 5 — Tests unitarios (5 archivos en `backend/tests/unit/`)

### 5a. `backend/tests/unit/jwt.unit.test.ts` (contenido completo):

```ts
import { describe, test, expect } from "bun:test";
import { signJwt, verifyJwt } from "../../src/utils/jwt";

const SECRET = "s3creto-de-prueba";

function b64url(s: string): string {
  return Buffer.from(s).toString("base64url");
}

function hmac(input: string, secret: string): string {
  const hasher = new Bun.CryptoHasher("sha256", secret);
  hasher.update(input);
  return hasher.digest("base64url") as string;
}

function craftToken(payload: Record<string, unknown>, secret: string): string {
  const h = b64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const p = b64url(JSON.stringify(payload));
  return `${h}.${p}.${hmac(`${h}.${p}`, secret)}`;
}

describe("signJwt / verifyJwt", () => {
  test("roundtrip: firma y verifica payload intacto con exp ~ now+900", () => {
    const token = signJwt({ userId: "u1", email: "a@b.com" }, SECRET, 900);
    const payload = verifyJwt(token, SECRET);
    expect(payload.userId).toBe("u1");
    expect(payload.email).toBe("a@b.com");
    const remaining = payload.exp - Math.floor(Date.now() / 1000);
    expect(remaining).toBeGreaterThanOrEqual(895);
    expect(remaining).toBeLessThanOrEqual(901);
  });

  test("token expirado lanza 'Token expired'", () => {
    const token = signJwt({ userId: "u1", email: "a@b.com" }, SECRET, -1);
    expect(() => verifyJwt(token, SECRET)).toThrow("Token expired");
  });

  test("firma adulterada lanza 'Invalid signature'", () => {
    const token = signJwt({ userId: "u1", email: "a@b.com" }, SECRET, 900);
    const last = token.slice(-1);
    const tampered = token.slice(0, -1) + (last === "A" ? "B" : "A");
    expect(() => verifyJwt(tampered, SECRET)).toThrow("Invalid signature");
  });

  test("secreto incorrecto lanza 'Invalid signature'", () => {
    const token = signJwt({ userId: "u1", email: "a@b.com" }, SECRET, 900);
    expect(() => verifyJwt(token, "otro-secreto")).toThrow("Invalid signature");
  });

  test("payload adulterado lanza 'Invalid signature'", () => {
    const token = signJwt({ userId: "u1", email: "a@b.com" }, SECRET, 900);
    const [h, , s] = token.split(".");
    const evil = b64url(
      JSON.stringify({ userId: "hacker", email: "a@b.com", exp: 9999999999 })
    );
    expect(() => verifyJwt(`${h}.${evil}.${s}`, SECRET)).toThrow("Invalid signature");
  });

  test("tokens malformados lanzan 'Invalid token format'", () => {
    expect(() => verifyJwt("abc", SECRET)).toThrow("Invalid token format");
    expect(() => verifyJwt("a.b", SECRET)).toThrow("Invalid token format");
  });

  test("payload sin userId lanza 'Missing userId'", () => {
    const exp = Math.floor(Date.now() / 1000) + 900;
    const token = craftToken({ email: "a@b.com", exp }, SECRET);
    expect(() => verifyJwt(token, SECRET)).toThrow("Missing userId");
  });

  test("exp no numérico lanza 'Missing exp'", () => {
    const token = craftToken({ userId: "u1", email: "a@b.com", exp: "mañana" }, SECRET);
    expect(() => verifyJwt(token, SECRET)).toThrow("Missing exp");
  });
});
```

### 5b. `backend/tests/unit/cookies.unit.test.ts` (contenido completo):

```ts
import { describe, test, expect } from "bun:test";
import { buildCookie, expireCookie, parseCookies } from "../../src/utils/cookies";

describe("buildCookie", () => {
  test("genera el string exacto con todos los flags", () => {
    const cookie = buildCookie("access_token", "abc", {
      httpOnly: true,
      secure: true,
      sameSite: "Lax",
      path: "/",
      maxAge: 900,
    });
    expect(cookie).toBe(
      "access_token=abc; Path=/; Max-Age=900; HttpOnly; Secure; SameSite=Lax"
    );
  });

  test("omite HttpOnly y Secure cuando son false", () => {
    const cookie = buildCookie("x", "1", {
      httpOnly: false,
      secure: false,
      sameSite: "Strict",
      path: "/p",
      maxAge: 10,
    });
    expect(cookie).toBe("x=1; Path=/p; Max-Age=10; SameSite=Strict");
  });
});

describe("expireCookie", () => {
  test("genera el string exacto de expiración", () => {
    expect(expireCookie("refresh_token", "/api/auth")).toBe(
      "refresh_token=; Path=/api/auth; Max-Age=0; HttpOnly; Secure; SameSite=Lax"
    );
  });
});

describe("parseCookies", () => {
  test("header null devuelve objeto vacío", () => {
    expect(parseCookies(null)).toEqual({});
  });

  test("header vacío devuelve objeto vacío", () => {
    expect(parseCookies("")).toEqual({});
  });

  test("parsea múltiples cookies y recorta espacios", () => {
    expect(parseCookies("a=1; b=2")).toEqual({ a: "1", b: "2" });
  });

  test("ignora fragmentos sin '='", () => {
    expect(parseCookies("a=1; basura; b=2")).toEqual({ a: "1", b: "2" });
  });

  test("decodifica valores URI-encoded", () => {
    expect(parseCookies("a=hello%20world")).toEqual({ a: "hello world" });
  });

  test("conserva el valor crudo si el encoding es inválido", () => {
    expect(parseCookies("a=%E0%A4%A")).toEqual({ a: "%E0%A4%A" });
  });

  test("divide solo en el primer '='", () => {
    expect(parseCookies("a=b=c")).toEqual({ a: "b=c" });
  });

  test("ignora cookies con nombre vacío", () => {
    expect(parseCookies("=v")).toEqual({});
  });
});
```

### 5c. `backend/tests/unit/authToken.unit.test.ts` (contenido completo):

```ts
import { describe, test, expect } from "bun:test";
import { generateRefreshToken, hashRefreshToken } from "../../src/utils/authToken";

describe("generateRefreshToken", () => {
  test("genera 64 caracteres hexadecimales", () => {
    expect(generateRefreshToken()).toMatch(/^[0-9a-f]{64}$/);
  });

  test("dos llamadas generan tokens distintos", () => {
    expect(generateRefreshToken()).not.toBe(generateRefreshToken());
  });
});

describe("hashRefreshToken", () => {
  test("es determinista y coincide con el vector sha256 conocido", () => {
    const expected =
      "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08";
    expect(hashRefreshToken("test")).toBe(expected);
    expect(hashRefreshToken("test")).toBe(hashRefreshToken("test"));
  });

  test("devuelve 64 caracteres hexadecimales", () => {
    expect(hashRefreshToken("cualquier-cosa")).toMatch(/^[0-9a-f]{64}$/);
  });

  test("string vacío lanza error", () => {
    expect(() => hashRefreshToken("")).toThrow("Token string cannot be empty.");
  });
});
```

### 5d. `backend/tests/unit/auth.unit.test.ts` (contenido completo — argon2id es lento, el hash se calcula una sola vez):

```ts
import { describe, test, expect, beforeAll } from "bun:test";
import { hashPassword, verifyPassword } from "../../src/utils/auth";

const PASSWORD = "MiClaveSegura#123";
let hash: string;

beforeAll(async () => {
  hash = await hashPassword(PASSWORD);
});

describe("hashPassword / verifyPassword", () => {
  test("el hash tiene formato saltHex(32):hashHex(64)", () => {
    const parts = hash.split(":");
    expect(parts.length).toBe(2);
    expect(parts[0]).toMatch(/^[0-9a-f]{32}$/);
    expect(parts[1]).toMatch(/^[0-9a-f]{64}$/);
  });

  test("verifica la contraseña correcta y rechaza la incorrecta", async () => {
    expect(await verifyPassword(PASSWORD, hash)).toBe(true);
    expect(await verifyPassword("otra-clave", hash)).toBe(false);
  });

  test("hash almacenado malformado devuelve false sin lanzar", async () => {
    expect(await verifyPassword("x", "basura-sin-dos-puntos")).toBe(false);
  });
});
```

### 5e. `backend/tests/unit/cors.unit.test.ts` (contenido completo — guarda y restaura `FRONTEND_ORIGIN` porque el env es global al proceso):

```ts
import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import { appendCorsHeaders, withCors, handlePreflight } from "../../src/utils/cors";
import { TEST_FRONTEND_ORIGIN } from "../helpers/constants";

const URL_BASE = "http://localhost/api/auth/login";

function reqWithOrigin(origin?: string): Request {
  const headers: Record<string, string> = {};
  if (origin) headers["Origin"] = origin;
  return new Request(URL_BASE, { method: "POST", headers });
}

beforeEach(() => {
  process.env.FRONTEND_ORIGIN = TEST_FRONTEND_ORIGIN;
});

afterEach(() => {
  process.env.FRONTEND_ORIGIN = TEST_FRONTEND_ORIGIN;
});

describe("appendCorsHeaders", () => {
  test("sin FRONTEND_ORIGIN configurado no agrega nada", () => {
    delete process.env.FRONTEND_ORIGIN;
    const headers = new Headers();
    appendCorsHeaders(headers, reqWithOrigin(TEST_FRONTEND_ORIGIN));
    expect(headers.get("Access-Control-Allow-Origin")).toBeNull();
    expect(headers.get("Access-Control-Allow-Credentials")).toBeNull();
  });

  test("con origin coincidente agrega los 3 headers", () => {
    const headers = new Headers();
    appendCorsHeaders(headers, reqWithOrigin(TEST_FRONTEND_ORIGIN));
    expect(headers.get("Access-Control-Allow-Origin")).toBe(TEST_FRONTEND_ORIGIN);
    expect(headers.get("Access-Control-Allow-Credentials")).toBe("true");
    expect(headers.get("Vary")).toBe("Origin");
  });

  test("con origin distinto no agrega nada", () => {
    const headers = new Headers();
    appendCorsHeaders(headers, reqWithOrigin("http://evil.example"));
    expect(headers.get("Access-Control-Allow-Origin")).toBeNull();
  });

  test("sin header Origin no agrega nada", () => {
    const headers = new Headers();
    appendCorsHeaders(headers, reqWithOrigin(undefined));
    expect(headers.get("Access-Control-Allow-Origin")).toBeNull();
  });
});

describe("handlePreflight", () => {
  test("con origin coincidente: 204 y todos los headers", () => {
    const res = handlePreflight(reqWithOrigin(TEST_FRONTEND_ORIGIN));
    expect(res.status).toBe(204);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe(TEST_FRONTEND_ORIGIN);
    expect(res.headers.get("Access-Control-Allow-Credentials")).toBe("true");
    expect(res.headers.get("Access-Control-Allow-Methods")).toBe("POST, OPTIONS");
    expect(res.headers.get("Access-Control-Allow-Headers")).toBe("Content-Type");
    expect(res.headers.get("Access-Control-Max-Age")).toBe("86400");
  });

  test("sin origin: 204 con headers de método pero sin Allow-Origin", () => {
    const res = handlePreflight(reqWithOrigin(undefined));
    expect(res.status).toBe(204);
    expect(res.headers.get("Access-Control-Allow-Methods")).toBe("POST, OPTIONS");
    expect(res.headers.get("Access-Control-Allow-Origin")).toBeNull();
  });
});

describe("withCors", () => {
  test("envuelve el handler conservando el body y agregando CORS", async () => {
    const wrapped = withCors(() => Response.json({ ok: true }));
    const res = await wrapped(reqWithOrigin(TEST_FRONTEND_ORIGIN));
    expect(await res.json()).toEqual({ ok: true });
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe(TEST_FRONTEND_ORIGIN);
    expect(res.headers.get("Access-Control-Allow-Credentials")).toBe("true");
  });
});
```

### 5f. Ejecutar `bun run test:unit` hasta que esté todo en verde (~34 casos, < 20 segundos). No avanzar con fallos.

---

## Paso 6 — Helpers de integración (`backend/tests/integration/helpers/`)

### 6a. `db.ts` (contenido completo — incluye la guarda de seguridad de dos capas):

```ts
import { sql } from "../../../src/db";
import { TEST_DB_NAME } from "../../helpers/constants";

if (!process.env.DATABASE_URL?.includes(TEST_DB_NAME)) {
  throw new Error(
    `SAFETY: DATABASE_URL no apunta a ${TEST_DB_NAME}. Abortando tests de integración.`
  );
}

export { sql };

export async function ensureTestDb(): Promise<void> {
  const [row] = await sql`SELECT current_database() AS db`;
  if (row.db !== TEST_DB_NAME) {
    throw new Error(
      `SAFETY: conectado a "${row.db}", se esperaba "${TEST_DB_NAME}". Abortando.`
    );
  }
}

export async function resetUsers(): Promise<void> {
  await sql`TRUNCATE TABLE users`;
}

export async function insertUser(
  email: string,
  passwordHash: string
): Promise<{ id: string; email: string }> {
  const [row] = await sql`
    INSERT INTO users (email, password_hash)
    VALUES (${email}, ${passwordHash})
    RETURNING id, email
  `;
  return row;
}

export async function getUserRow(email: string) {
  const [row] = await sql`SELECT * FROM users WHERE email = ${email}`;
  return row ?? null;
}

export async function setUserState(
  email: string,
  failedAttempts: number,
  lockedUntil: Date | null
): Promise<void> {
  await sql`
    UPDATE users
    SET failed_attempts = ${failedAttempts}, locked_until = ${lockedUntil}
    WHERE email = ${email}
  `;
}
```

### 6b. `fixtures.ts` (contenido completo — el hash argon2id se calcula UNA vez por proceso):

```ts
import { hashPassword } from "../../../src/utils/auth";

export const TEST_USER = {
  email: "test.user@example.com",
  password: "Sup3rSecreta!",
};

export const WRONG_PASSWORD = "contrasena-incorrecta-123";

let cached: Promise<string> | null = null;

export function getTestPasswordHash(): Promise<string> {
  if (!cached) cached = hashPassword(TEST_USER.password);
  return cached;
}
```

### 6c. `server.ts` (contenido completo):

```ts
import { createServer } from "../../../src/server";

export function startTestServer() {
  const server = createServer(0);
  return { server, baseUrl: `http://localhost:${server.port}` };
}
```

### 6d. `http.ts` (contenido completo):

```ts
export async function postJson(
  baseUrl: string,
  path: string,
  body: unknown,
  headers: Record<string, string> = {}
): Promise<Response> {
  return fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

export interface CookieInfo {
  value: string;
  raw: string;
}

export function getSetCookieMap(res: Response): Map<string, CookieInfo> {
  const map = new Map<string, CookieInfo>();
  for (const raw of res.headers.getSetCookie()) {
    const first = raw.split(";")[0];
    const idx = first.indexOf("=");
    if (idx === -1) continue;
    map.set(first.slice(0, idx).trim(), { value: first.slice(idx + 1), raw });
  }
  return map;
}
```

### 6e. `audit.ts` (contenido completo — `auditLog` escribe con `appendFileSync`, así que al resolver el fetch la línea ya está en disco):

```ts
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

function auditLogPath(): string {
  const date = new Date().toISOString().slice(0, 10);
  return join(process.cwd(), "logs", `audit-${date}.log`);
}

export function auditLineCount(): number {
  const p = auditLogPath();
  if (!existsSync(p)) return 0;
  return readFileSync(p, "utf-8").split("\n").filter((l) => l.trim()).length;
}

export function readAuditEntriesAfter(count: number): Array<Record<string, string>> {
  const p = auditLogPath();
  if (!existsSync(p)) return [];
  return readFileSync(p, "utf-8")
    .split("\n")
    .filter((l) => l.trim())
    .slice(count)
    .map((l) => JSON.parse(l));
}
```

---

## Paso 7 — Tests de integración (5 archivos en `backend/tests/integration/`)

Crear los archivos de a uno, ejecutando `bun run test:integration` después de cada uno. No avanzar con fallos.

### 7a. `login.int.test.ts` (contenido completo):

```ts
import { describe, test, expect, beforeAll, beforeEach, afterAll } from "bun:test";
import { ensureTestDb, resetUsers, insertUser, getUserRow } from "./helpers/db";
import { TEST_USER, WRONG_PASSWORD, getTestPasswordHash } from "./helpers/fixtures";
import { startTestServer } from "./helpers/server";
import { postJson, getSetCookieMap } from "./helpers/http";
import { auditLineCount, readAuditEntriesAfter } from "./helpers/audit";
import { verifyJwt } from "../../src/utils/jwt";
import { hashRefreshToken } from "../../src/utils/authToken";
import { TEST_JWT_SECRET } from "../helpers/constants";

const GENERIC = "Correo electrónico o contraseña incorrectos";

let server: ReturnType<typeof startTestServer>["server"];
let baseUrl: string;
let passwordHash: string;
let userId: string;

beforeAll(async () => {
  await ensureTestDb();
  passwordHash = await getTestPasswordHash();
  const started = startTestServer();
  server = started.server;
  baseUrl = started.baseUrl;
});

afterAll(async () => {
  await server.stop(true);
});

beforeEach(async () => {
  await resetUsers();
  const user = await insertUser(TEST_USER.email, passwordHash);
  userId = user.id;
});

describe("POST /api/auth/login", () => {
  test("login exitoso: 200, dos cookies exactas, JWT válido, hash en DB y auditoría", async () => {
    const before = auditLineCount();

    const res = await postJson(baseUrl, "/api/auth/login", {
      email: TEST_USER.email,
      password: TEST_USER.password,
    });

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ message: "Login exitoso" });

    const cookies = getSetCookieMap(res);
    expect(cookies.size).toBe(2);

    const access = cookies.get("access_token");
    const refresh = cookies.get("refresh_token");
    expect(access).toBeDefined();
    expect(refresh).toBeDefined();
    expect(access!.raw).toBe(
      `access_token=${access!.value}; Path=/; Max-Age=900; HttpOnly; Secure; SameSite=Lax`
    );
    expect(refresh!.raw).toBe(
      `refresh_token=${refresh!.value}; Path=/api/auth; Max-Age=604800; HttpOnly; Secure; SameSite=Lax`
    );

    const payload = verifyJwt(access!.value, TEST_JWT_SECRET);
    expect(payload.email).toBe(TEST_USER.email);
    expect(payload.userId).toBe(userId);
    const remaining = payload.exp - Math.floor(Date.now() / 1000);
    expect(remaining).toBeGreaterThanOrEqual(895);
    expect(remaining).toBeLessThanOrEqual(901);

    expect(refresh!.value).toMatch(/^[0-9a-f]{64}$/);
    const row = await getUserRow(TEST_USER.email);
    expect(row.refresh_token_hash).toBe(hashRefreshToken(refresh!.value));

    const entries = readAuditEntriesAfter(before);
    expect(entries.length).toBe(1);
    expect(entries[0]).toMatchObject({
      event: "LOGIN_SUCCESS",
      email: TEST_USER.email,
      result: "success",
    });
  });

  test("contraseña incorrecta: 401 genérico, sin cookies, auditoría invalid_password", async () => {
    const before = auditLineCount();

    const res = await postJson(baseUrl, "/api/auth/login", {
      email: TEST_USER.email,
      password: WRONG_PASSWORD,
    });

    expect(res.status).toBe(401);
    expect(res.headers.get("Content-Type")).toContain("application/problem+json");
    const body = await res.json();
    expect(body.detail).toBe(GENERIC);
    expect(res.headers.getSetCookie().length).toBe(0);

    const entries = readAuditEntriesAfter(before);
    expect(entries.length).toBe(1);
    expect(entries[0]).toMatchObject({
      event: "LOGIN_FAILURE",
      email: TEST_USER.email,
      result: "invalid_password",
    });
  });

  test("email inexistente: 401 con el MISMO mensaje genérico (R4), auditoría user_not_found", async () => {
    const before = auditLineCount();

    const res = await postJson(baseUrl, "/api/auth/login", {
      email: "noexiste@example.com",
      password: WRONG_PASSWORD,
    });

    expect(res.status).toBe(401);
    const body = await res.json();
    expect(body.detail).toBe(GENERIC);
    expect(res.headers.getSetCookie().length).toBe(0);

    const entries = readAuditEntriesAfter(before);
    expect(entries.length).toBe(1);
    expect(entries[0]).toMatchObject({
      event: "LOGIN_FAILURE",
      email: "noexiste@example.com",
      result: "user_not_found",
    });
  });

  test("body que no es JSON: 400 Invalid JSON body", async () => {
    const res = await postJson(baseUrl, "/api/auth/login", "{esto no es json");
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.detail).toBe("Invalid JSON body");
  });

  test("falla de validación zod: 400 con detalle de errores", async () => {
    const res = await postJson(baseUrl, "/api/auth/login", {
      email: "no-es-email",
      password: "",
    });
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.detail).toBe("Validation failed");
    expect(Array.isArray(body.errors)).toBe(true);
    expect(body.errors.length).toBeGreaterThan(0);
  });

  test("JWT_SECRET ausente: 500 del manejador de errores de producción", async () => {
    const saved = process.env.JWT_SECRET;
    delete process.env.JWT_SECRET;
    try {
      const res = await postJson(baseUrl, "/api/auth/login", {
        email: TEST_USER.email,
        password: TEST_USER.password,
      });
      expect(res.status).toBe(500);
      const body = await res.json();
      expect(body.detail).toBe("Error interno del servidor");
    } finally {
      process.env.JWT_SECRET = saved;
    }
  });
});
```

### 7b. `refresh.int.test.ts` (contenido completo):

```ts
import { describe, test, expect, beforeAll, beforeEach, afterAll } from "bun:test";
import { ensureTestDb, resetUsers, insertUser, getUserRow } from "./helpers/db";
import { TEST_USER, getTestPasswordHash } from "./helpers/fixtures";
import { startTestServer } from "./helpers/server";
import { postJson, getSetCookieMap } from "./helpers/http";
import { auditLineCount, readAuditEntriesAfter } from "./helpers/audit";
import { hashRefreshToken } from "../../src/utils/authToken";

const SESSION_ERROR = "Sesión inválida o expirada";

let server: ReturnType<typeof startTestServer>["server"];
let baseUrl: string;
let passwordHash: string;

beforeAll(async () => {
  await ensureTestDb();
  passwordHash = await getTestPasswordHash();
  const started = startTestServer();
  server = started.server;
  baseUrl = started.baseUrl;
});

afterAll(async () => {
  await server.stop(true);
});

beforeEach(async () => {
  await resetUsers();
  await insertUser(TEST_USER.email, passwordHash);
});

async function loginAndGetRefreshToken(): Promise<string> {
  const res = await postJson(baseUrl, "/api/auth/login", {
    email: TEST_USER.email,
    password: TEST_USER.password,
  });
  expect(res.status).toBe(200);
  return getSetCookieMap(res).get("refresh_token")!.value;
}

describe("POST /api/auth/refresh", () => {
  test("refresh exitoso: 200, cookies nuevas, rotación persistida y auditoría", async () => {
    const oldToken = await loginAndGetRefreshToken();
    const before = auditLineCount();

    const res = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: "POST",
      headers: { Cookie: `refresh_token=${oldToken}` },
    });

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ message: "Sesión renovada" });

    const cookies = getSetCookieMap(res);
    expect(cookies.size).toBe(2);
    const newToken = cookies.get("refresh_token")!.value;
    expect(newToken).toMatch(/^[0-9a-f]{64}$/);
    expect(newToken).not.toBe(oldToken);

    const row = await getUserRow(TEST_USER.email);
    expect(row.refresh_token_hash).toBe(hashRefreshToken(newToken));

    const entries = readAuditEntriesAfter(before);
    expect(entries.length).toBe(1);
    expect(entries[0]).toMatchObject({
      event: "REFRESH_SUCCESS",
      email: TEST_USER.email,
      result: "success",
    });
  });

  test("la rotación mata el token anterior: replay → 401", async () => {
    const oldToken = await loginAndGetRefreshToken();
    const first = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: "POST",
      headers: { Cookie: `refresh_token=${oldToken}` },
    });
    expect(first.status).toBe(200);

    const before = auditLineCount();
    const replay = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: "POST",
      headers: { Cookie: `refresh_token=${oldToken}` },
    });

    expect(replay.status).toBe(401);
    const body = await replay.json();
    expect(body.detail).toBe(SESSION_ERROR);

    const entries = readAuditEntriesAfter(before);
    expect(entries.length).toBe(1);
    expect(entries[0]).toMatchObject({
      event: "REFRESH_FAILURE",
      result: "token_not_found",
    });
  });

  test("sin header Cookie: 401 y auditoría missing_cookie", async () => {
    const before = auditLineCount();
    const res = await fetch(`${baseUrl}/api/auth/refresh`, { method: "POST" });

    expect(res.status).toBe(401);
    const body = await res.json();
    expect(body.detail).toBe(SESSION_ERROR);

    const entries = readAuditEntriesAfter(before);
    expect(entries.length).toBe(1);
    expect(entries[0]).toMatchObject({
      event: "REFRESH_FAILURE",
      result: "missing_cookie",
    });
  });

  test("token basura: 401 token_not_found", async () => {
    const before = auditLineCount();
    const res = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: "POST",
      headers: { Cookie: "refresh_token=deadbeef" },
    });

    expect(res.status).toBe(401);
    const entries = readAuditEntriesAfter(before);
    expect(entries[0]).toMatchObject({
      event: "REFRESH_FAILURE",
      result: "token_not_found",
    });
  });

  test("solo cookie de access (sin refresh): 401 missing_cookie", async () => {
    const res = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: "POST",
      headers: { Cookie: "access_token=loquesea" },
    });
    expect(res.status).toBe(401);
    const body = await res.json();
    expect(body.detail).toBe(SESSION_ERROR);
  });
});
```

### 7c. `logout.int.test.ts` (contenido completo):

```ts
import { describe, test, expect, beforeAll, beforeEach, afterAll } from "bun:test";
import { ensureTestDb, resetUsers, insertUser, getUserRow } from "./helpers/db";
import { TEST_USER, getTestPasswordHash } from "./helpers/fixtures";
import { startTestServer } from "./helpers/server";
import { postJson, getSetCookieMap } from "./helpers/http";
import { auditLineCount, readAuditEntriesAfter } from "./helpers/audit";

let server: ReturnType<typeof startTestServer>["server"];
let baseUrl: string;
let passwordHash: string;

beforeAll(async () => {
  await ensureTestDb();
  passwordHash = await getTestPasswordHash();
  const started = startTestServer();
  server = started.server;
  baseUrl = started.baseUrl;
});

afterAll(async () => {
  await server.stop(true);
});

beforeEach(async () => {
  await resetUsers();
  await insertUser(TEST_USER.email, passwordHash);
});

async function loginAndGetRefreshToken(): Promise<string> {
  const res = await postJson(baseUrl, "/api/auth/login", {
    email: TEST_USER.email,
    password: TEST_USER.password,
  });
  expect(res.status).toBe(200);
  return getSetCookieMap(res).get("refresh_token")!.value;
}

describe("POST /api/auth/logout", () => {
  test("logout con sesión: 200, cookies expiradas exactas, hash NULL y auditoría", async () => {
    const token = await loginAndGetRefreshToken();
    const before = auditLineCount();

    const res = await fetch(`${baseUrl}/api/auth/logout`, {
      method: "POST",
      headers: { Cookie: `refresh_token=${token}` },
    });

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ message: "Sesión cerrada" });

    const rawCookies = res.headers.getSetCookie();
    expect(rawCookies.length).toBe(2);
    expect(rawCookies).toContain(
      "access_token=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax"
    );
    expect(rawCookies).toContain(
      "refresh_token=; Path=/api/auth; Max-Age=0; HttpOnly; Secure; SameSite=Lax"
    );

    const row = await getUserRow(TEST_USER.email);
    expect(row.refresh_token_hash).toBeNull();

    const entries = readAuditEntriesAfter(before);
    expect(entries.length).toBe(1);
    expect(entries[0]).toMatchObject({
      event: "LOGOUT",
      email: TEST_USER.email,
      result: "success",
    });
  });

  test("logout sin cookie: 200 idempotente con cookies expiradas y auditoría no_session", async () => {
    const before = auditLineCount();

    const res = await fetch(`${baseUrl}/api/auth/logout`, { method: "POST" });

    expect(res.status).toBe(200);
    expect(res.headers.getSetCookie().length).toBe(2);

    const entries = readAuditEntriesAfter(before);
    expect(entries.length).toBe(1);
    expect(entries[0]).toMatchObject({ event: "LOGOUT", result: "no_session" });
  });

  test("refresh después de logout: 401 (la sesión murió de verdad)", async () => {
    const token = await loginAndGetRefreshToken();

    const logout = await fetch(`${baseUrl}/api/auth/logout`, {
      method: "POST",
      headers: { Cookie: `refresh_token=${token}` },
    });
    expect(logout.status).toBe(200);

    const refresh = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: "POST",
      headers: { Cookie: `refresh_token=${token}` },
    });
    expect(refresh.status).toBe(401);
  });
});
```

### 7d. `bruteforce.int.test.ts` (contenido completo — los 3 tests llevan timeout explícito de 60 s porque cada verificación argon2id tarda cientos de ms):

```ts
import { describe, test, expect, beforeAll, beforeEach, afterEach, afterAll } from "bun:test";
import { ensureTestDb, resetUsers, insertUser, getUserRow, setUserState } from "./helpers/db";
import { TEST_USER, WRONG_PASSWORD, getTestPasswordHash } from "./helpers/fixtures";
import { startTestServer } from "./helpers/server";
import { postJson } from "./helpers/http";
import { auditLineCount, readAuditEntriesAfter } from "./helpers/audit";

const GENERIC = "Correo electrónico o contraseña incorrectos";

let server: ReturnType<typeof startTestServer>["server"];
let baseUrl: string;
let passwordHash: string;

beforeAll(async () => {
  await ensureTestDb();
  passwordHash = await getTestPasswordHash();
  const started = startTestServer();
  server = started.server;
  baseUrl = started.baseUrl;
});

afterAll(async () => {
  await server.stop(true);
});

beforeEach(async () => {
  await resetUsers();
  await insertUser(TEST_USER.email, passwordHash);
});

afterEach(() => {
  process.env.FEATURE_FLAG_BRUTE_FORCE = "false";
});

function attemptLogin(password: string): Promise<Response> {
  return postJson(baseUrl, "/api/auth/login", {
    email: TEST_USER.email,
    password,
  });
}

describe("Prevención de fuerza bruta (R5)", () => {
  test(
    "flag OFF: 6 fallos consecutivos NO bloquean y el 7º intento correcto entra (criterio de aceptación)",
    async () => {
      process.env.FEATURE_FLAG_BRUTE_FORCE = "false";
      const before = auditLineCount();

      for (let i = 0; i < 6; i++) {
        const res = await attemptLogin(WRONG_PASSWORD);
        expect(res.status).toBe(401);
        const body = await res.json();
        expect(body.detail).toBe(GENERIC);
      }

      const row = await getUserRow(TEST_USER.email);
      expect(row.failed_attempts).toBe(0);
      expect(row.locked_until).toBeNull();

      const seventh = await attemptLogin(TEST_USER.password);
      expect(seventh.status).toBe(200);

      const entries = readAuditEntriesAfter(before);
      expect(entries.length).toBe(7);
      for (let i = 0; i < 6; i++) {
        expect(entries[i]).toMatchObject({
          event: "LOGIN_FAILURE",
          result: "invalid_password",
        });
      }
      expect(entries[6]).toMatchObject({ event: "LOGIN_SUCCESS", result: "success" });
    },
    60000
  );

  test(
    "flag ON: 5 fallos bloquean la cuenta; el 6º intento con contraseña CORRECTA da 401",
    async () => {
      process.env.FEATURE_FLAG_BRUTE_FORCE = "true";

      for (let i = 0; i < 5; i++) {
        const res = await attemptLogin(WRONG_PASSWORD);
        expect(res.status).toBe(401);
      }

      const row = await getUserRow(TEST_USER.email);
      expect(row.failed_attempts).toBe(5);
      expect(row.locked_until).not.toBeNull();

      const before = auditLineCount();
      const locked = await attemptLogin(TEST_USER.password);
      expect(locked.status).toBe(401);
      const body = await locked.json();
      expect(body.detail).toBe(GENERIC);

      const entries = readAuditEntriesAfter(before);
      expect(entries.length).toBe(1);
      expect(entries[0]).toMatchObject({
        event: "LOGIN_FAILURE",
        result: "account_locked",
      });
    },
    60000
  );

  test(
    "flag ON: con el bloqueo expirado el login correcto entra y resetea contadores",
    async () => {
      process.env.FEATURE_FLAG_BRUTE_FORCE = "true";
      await setUserState(TEST_USER.email, 5, new Date(Date.now() - 60_000));

      const res = await attemptLogin(TEST_USER.password);
      expect(res.status).toBe(200);

      const row = await getUserRow(TEST_USER.email);
      expect(row.failed_attempts).toBe(0);
      expect(row.locked_until).toBeNull();
    },
    60000
  );
});
```

### 7e. `cors.int.test.ts` (contenido completo — el preload garantiza `FRONTEND_ORIGIN=http://localhost:3001`):

```ts
import { describe, test, expect, beforeAll, beforeEach, afterAll } from "bun:test";
import { ensureTestDb, resetUsers, insertUser } from "./helpers/db";
import { TEST_USER, getTestPasswordHash } from "./helpers/fixtures";
import { startTestServer } from "./helpers/server";
import { postJson } from "./helpers/http";
import { TEST_FRONTEND_ORIGIN } from "../helpers/constants";

let server: ReturnType<typeof startTestServer>["server"];
let baseUrl: string;
let passwordHash: string;

beforeAll(async () => {
  await ensureTestDb();
  passwordHash = await getTestPasswordHash();
  const started = startTestServer();
  server = started.server;
  baseUrl = started.baseUrl;
});

afterAll(async () => {
  await server.stop(true);
});

beforeEach(async () => {
  await resetUsers();
  await insertUser(TEST_USER.email, passwordHash);
});

describe("CORS", () => {
  test("preflight con origin permitido: 204 y headers completos", async () => {
    const res = await fetch(`${baseUrl}/api/auth/login`, {
      method: "OPTIONS",
      headers: {
        Origin: TEST_FRONTEND_ORIGIN,
        "Access-Control-Request-Method": "POST",
      },
    });

    expect(res.status).toBe(204);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe(TEST_FRONTEND_ORIGIN);
    expect(res.headers.get("Access-Control-Allow-Credentials")).toBe("true");
    expect(res.headers.get("Vary")).toBe("Origin");
    expect(res.headers.get("Access-Control-Allow-Methods")).toBe("POST, OPTIONS");
    expect(res.headers.get("Access-Control-Allow-Headers")).toBe("Content-Type");
    expect(res.headers.get("Access-Control-Max-Age")).toBe("86400");
  });

  test("preflight con origin NO permitido: 204 sin Allow-Origin", async () => {
    const res = await fetch(`${baseUrl}/api/auth/login`, {
      method: "OPTIONS",
      headers: {
        Origin: "http://evil.example",
        "Access-Control-Request-Method": "POST",
      },
    });

    expect(res.status).toBe(204);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBeNull();
  });

  test("POST login con origin permitido lleva los headers CORS (withCors)", async () => {
    const res = await postJson(
      baseUrl,
      "/api/auth/login",
      { email: TEST_USER.email, password: TEST_USER.password },
      { Origin: TEST_FRONTEND_ORIGIN }
    );

    expect(res.status).toBe(200);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe(TEST_FRONTEND_ORIGIN);
    expect(res.headers.get("Access-Control-Allow-Credentials")).toBe("true");
  });

  test("POST login sin header Origin no lleva headers CORS", async () => {
    const res = await postJson(baseUrl, "/api/auth/login", {
      email: TEST_USER.email,
      password: TEST_USER.password,
    });

    expect(res.status).toBe(200);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBeNull();
  });

  test("ruta inexistente: 404 problem+json CON headers CORS (fallback fetch)", async () => {
    const res = await postJson(
      baseUrl,
      "/api/auth/noexiste",
      {},
      { Origin: TEST_FRONTEND_ORIGIN }
    );

    expect(res.status).toBe(404);
    const body = await res.json();
    expect(body.detail).toBe("Ruta no encontrada");
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe(TEST_FRONTEND_ORIGIN);
  });
});
```

---

## Paso 8 — Verificación final

Desde `backend/` (Postgres healthy):

| Comando | Resultado esperado |
|---|---|
| `bun run test:setup-db` | `Migración aplicada a construerp_test.`, exit 0 (también al re-ejecutar) |
| `docker exec construerp-db psql -U construerp -d construerp_test -c "\dt"` | tabla `users` listada |
| `bun run test:unit` | ~34 pass, 0 fail, < 20 s |
| `bun run test:integration` | ~22 pass, 0 fail (el archivo de fuerza bruta es el lento) |
| `bun run test` | ambas suites en verde, exit 0 |
| `bun run start` | `Server running on http://localhost:3000` (refactor no rompió producción) |
| `docker exec construerp-db psql -U construerp -d construerp_db -c "SELECT count(*) FROM users;"` | mismo conteo que antes de correr los tests (la DB dev quedó intacta) |

**Demo negativa (probar que los tests detectan regresiones):** en `login.int.test.ts` cambiar temporalmente `const GENERIC = "Correo electrónico o contraseña incorrectos"` por `const GENERIC = "X"`, ejecutar `bun run test:integration` → deben fallar exactamente los tests que asertan el mensaje genérico (3). Revertir el cambio y volver a correr en verde.

### Checklist de finalización

- [ ] `bunfig.toml`, `tests/preload.ts`, `tests/helpers/constants.ts` creados
- [ ] `src/server.ts` creado e `index.ts` reemplazado; `bun run start` funciona
- [ ] `scripts/setup-test-db.ts` creado e idempotente
- [ ] `tsconfig.json` (include) y `package.json` (scripts) actualizados
- [ ] 5 archivos unitarios en verde (`bun run test:unit`)
- [ ] 5 helpers + 5 archivos de integración en verde (`bun run test:integration`)
- [ ] `bun run test` completo en verde
- [ ] DB de desarrollo intacta
- [ ] Demo negativa ejecutada y revertida

---

## Riesgos residuales (qué hacer si algo falla)

1. **`ensureTestDb` reporta `construerp_db`:** el `sql` global capturó el env antes del preload (comportamiento no documentado de la versión de Bun). La suite aborta sola (esa es la guarda). Solución de respaldo: eliminar `bunfig.toml` y prefijar los scripts de test con `DATABASE_URL=postgresql://construerp:construerp_dev@localhost:5432/construerp_test JWT_SECRET=... bun test ...` (el shell de Bun soporta prefijos `VAR=valor` también en Windows). Reportar al usuario si esto ocurre.
2. **Tests de fuerza bruta exceden timeout:** subir el `--timeout` del script y/o el timeout por test (tercer argumento de `test(...)`). No reestructurar.
3. **`getSetCookie()` no existe / devuelve undefined:** detenerse y reportar (no parsear `headers.get("set-cookie")` a mano sin avisar).
4. **`server.stop(true)` cuelga en `afterAll`:** verificar que se pasó `true` (cierre forzado de conexiones).
5. **Test corriendo justo a medianoche UTC:** el snapshot de auditoría puede cruzar de archivo y fallar una vez. Re-ejecutar.
6. **`bun run test:setup-db` falla al crear la DB:** verificar que el contenedor está healthy y que el puerto 5432 no está ocupado por otro Postgres local.
