---
name: guia-tecnica-codigo
description: Genera guías técnicas educativas en LaTeX para asignaturas de programación, con teoría, ejemplos de código resueltos y ejercicios graduados. La salida SIEMPRE es un archivo .tex compilable. Usa esta skill siempre que el usuario pida una guía, apunte, material de estudio, dossier, cuadernillo, set de ejercicios o documento didáctico sobre cualquier tema de código o ciencias de la computación (Python, C, Java, SQL, JavaScript, algoritmos, estructuras de datos, recursividad, POO, bases de datos, etc.), incluso si no menciona "LaTeX" explícitamente. Úsala también cuando pidan convertir notas o un temario en material formateado para estudiantes.
---

# Guía técnica educativa para asignaturas de código (salida LaTeX)

Produce un documento `.tex` listo para compilar que enseña un tema de
programación combinando explicación conceptual, código resuelto y ejercicios.
El objetivo pedagógico manda: una guía no es un volcado de teoría, es una ruta
que lleva al estudiante de no saber a poder resolver problemas por sí mismo.

## Flujo de trabajo

1. **Lee el tema y el público.** Identifica: qué lenguaje, qué nivel
   (introductorio / intermedio / avanzado), y qué debe lograr el estudiante.
   Si el usuario no especifica el nivel o el lenguaje y el tema lo admite en
   varios, pregunta una sola vez antes de generar; no inventes un nivel.
2. **Copia la plantilla.** Parte SIEMPRE de `assets/plantilla-guia.tex`. No
   escribas un `.tex` desde cero: la plantilla ya trae el preámbulo verificado
   (cajas, resaltado de código, numeración de ejercicios, encabezados).
3. **Ajusta el lenguaje.** Cambia `language=Python` en `\lstset` por el que
   corresponda. Para lenguajes sin soporte nativo (JavaScript, TypeScript),
   consulta `references/listings-lenguajes.md`.
4. **Rellena el contenido** respetando la estructura obligatoria de abajo.
   Sustituye todos los marcadores `<<...>>` por contenido real. No dejes ningún
   marcador sin reemplazar.
5. **Compila para verificar** si hay un compilador disponible:
   `pdflatex archivo.tex` dos veces (la segunda fija índices y referencias).
   Si compila, entrega el `.tex` (y el PDF si el usuario lo quiere). Si no hay
   compilador, entrega el `.tex` y avisa que se compila con pdflatex/Overleaf.
6. **Entrega el `.tex` como archivo**, no como bloque de texto en el chat.

## Estructura obligatoria de toda guía

Respeta este orden. Cada sección tiene una razón pedagógica; no la omitas salvo
que el usuario lo pida.

1. **Portada** — título, asignatura, unidad, autor/institución, fecha.
2. **Objetivos de aprendizaje** — qué sabrá HACER el estudiante al terminar.
   Usa verbos medibles (implementar, trazar, distinguir, comparar), no vagos
   ("entender", "conocer"). Van en la caja `objetivos`.
3. **Conocimientos previos** — qué debe dominar de antemano. Evita que el
   estudiante choque con un prerrequisito a mitad de camino.
4. **Desarrollo conceptual** — la teoría, de lo simple a lo complejo. Introduce
   un concepto, defínelo (caja `definicion`), y solo entonces avanza al
   siguiente. Cada idea nueva debe apoyarse en la anterior.
5. **Ejemplos resueltos** — código real, completo y comentado, con explicación
   de por qué funciona (caja `ejemplo` + bloque `lstlisting`). El ejemplo debe
   poder ejecutarse tal cual; no uses pseudocódigo si el tema es un lenguaje
   concreto.
6. **Ejercicios propuestos** — graduados de menor a mayor dificultad, con
   etiqueta `[básico]`, `[intermedio]`, `[desafío]`. Se numeran solos con la
   caja `ejercicio`. Incluye al menos uno que exija razonamiento, no solo
   reproducir el ejemplo.
7. **Soluciones** — al final (o en página aparte), para no revelarlas antes de
   que el estudiante lo intente.
8. **Referencias** — fuentes; si hay URLs, con fecha de consulta.

## Principios de contenido (no negociables)

- **Progresión real.** Ordena el material por dependencia conceptual, no por
  capricho. Si el concepto B necesita A, A va primero.
- **Mostrar y luego pedir.** Todo tipo de ejercicio debe tener un ejemplo
  resuelto análogo antes. No pidas algo que no se enseñó.
- **Ejercicios que escalan.** El primer ejercicio refuerza; el último obliga a
  pensar o a extender lo visto. Evita tres ejercicios que sean el mismo problema
  con números distintos.
- **Código ejecutable.** El código de los ejemplos y soluciones debe ser
  correcto y ejecutable, no aproximado. Verifica la lógica antes de escribirlo.
- **Cajas con propósito.** `nota` para aclaraciones útiles, `advertencia` para
  errores comunes que el estudiante cometerá. No las uses de adorno.

## Cajas disponibles en la plantilla

| Caja                       | Para qué                                       |
|----------------------------|------------------------------------------------|
| `objetivos`                | Lista de objetivos de aprendizaje              |
| `definicion{término}`      | Definición formal de un concepto               |
| `ejemplo{descripción}`     | Encabezar un ejemplo resuelto                  |
| `nota`                     | Aclaración o dato útil                         |
| `advertencia`              | Error común / trampa a evitar                  |
| `ejercicio[dificultad]`    | Ejercicio (se numera automáticamente)          |

El `[dificultad]` de `ejercicio` es opcional; si lo omites, sale solo el número.

## Detalles técnicos del preámbulo

- **Acentos en código:** `\lstset` ya incluye reglas `literate` para que los
  acentos y la ñ se vean bien dentro de `lstlisting`. No las quites.
- **Guiones bajos en texto:** nunca escribas `_` en texto normal (rompe la
  compilación). En nombres de variables dentro de prosa usa `\texttt{nombre\_var}`
  con la barra invertida, o ponlos dentro de `\lstinline`. Dentro de
  `lstlisting` el guion bajo es seguro.
- **Idioma:** la plantilla usa `\usepackage[spanish,es-noquoting]{babel}`. Esto
  requiere el paquete `babel-spanish`, presente en Overleaf y en TeX Live
  completo. Si el entorno de compilación no lo tiene, cámbialo por
  `\usepackage[english]{babel}` (solo cambia la separación silábica, no el
  contenido).
- **Compilar dos veces** para que la numeración de página y las referencias
  queden correctas.

## Archivos de la skill

- `assets/plantilla-guia.tex` — plantilla base verificada. Punto de partida
  obligatorio. El ejemplo incluido es una guía de recursividad en Python que
  sirve de modelo del tono y la densidad esperados.
- `references/listings-lenguajes.md` — cómo configurar el resaltado para C,
  Java, SQL, JavaScript, TypeScript y otros, y cómo mezclar lenguajes.
