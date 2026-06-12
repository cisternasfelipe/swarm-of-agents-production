# Configuración de `listings` por lenguaje

La plantilla usa `\lstset{... language=Python ...}`. Para adaptar la guía a otra
asignatura, cambia el valor de `language=` y, si hace falta, ajusta palabras
clave o el carácter de comentario. `listings` ya conoce la mayoría de lenguajes;
solo defines el lenguaje y conserva el resto del estilo (colores, números de
línea, marco).

## Lenguajes con soporte nativo en `listings`

Basta con `language=NOMBRE`:

| Asignatura típica        | Valor de `language=` |
|--------------------------|----------------------|
| Python                   | `Python`             |
| C                        | `C`                  |
| C++                      | `C++`                |
| Java                     | `Java`               |
| SQL                      | `SQL`                |
| HTML                     | `HTML`               |
| PHP                      | `PHP`                |
| Bash / shell             | `bash`               |
| MATLAB / Octave          | `Matlab`             |
| R                        | `R`                  |
| Pascal                   | `Pascal`             |

Ejemplo para una asignatura de C:

```latex
\lstset{
  language=C,
  % ... el resto del bloque de la plantilla queda igual ...
}
```

## Lenguajes sin soporte nativo (definir manualmente)

Algunos lenguajes modernos no vienen en `listings`. Defínelos con
`\lstdefinelanguage` en el preámbulo y luego usa ese nombre.

### JavaScript / TypeScript

```latex
\lstdefinelanguage{JavaScript}{
  keywords={break,case,catch,const,continue,debugger,default,delete,do,else,
    export,extends,finally,for,function,if,import,in,instanceof,let,new,
    return,super,switch,this,throw,try,typeof,var,void,while,with,yield,
    async,await,of,class},
  sensitive=true,
  comment=[l]{//},
  morecomment=[s]{/*}{*/},
  morestring=[b]',
  morestring=[b]",
  morestring=[b]`
}
% Uso: \lstset{language=JavaScript, ...}
```

Para TypeScript, añade a `keywords`: `interface, type, enum, implements,
public, private, protected, readonly, namespace, declare, abstract`.

### Otros lenguajes
Patrón general: `keywords={...}` para palabras reservadas, `comment=[l]{...}`
para comentario de línea, `morecomment=[s]{...}{...}` para comentario de bloque,
`morestring=[b]"` para cadenas, `sensitive=true` si distingue mayúsculas.

## Resaltar más de un lenguaje en la misma guía

Si una guía mezcla, por ejemplo, SQL y Python, no cambies `\lstset` global.
Usa el parámetro `language` por bloque:

```latex
\begin{lstlisting}[language=SQL]
SELECT nombre FROM alumnos WHERE nota >= 4.0;
\end{lstlisting}

\begin{lstlisting}[language=Python]
print("Hola")
\end{lstlisting}
```

## Alternativa de mayor calidad: `minted`

`minted` da resaltado superior (usa Pygments) pero requiere Python con Pygments
instalado y compilar con la opción `-shell-escape`. Es más frágil y NO funciona
en algunos Overleaf gratuitos sin configuración. Usa `listings` por defecto;
recurre a `minted` solo si el usuario lo pide explícitamente y confirma que su
entorno lo permite.
