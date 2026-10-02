# Avance 5 — Detección de errores (parte 1)

**Curso:** CI0124 Computabilidad y Complejidad · **Proyecto 1:** Rutas en Internet

Este avance rehace el manejo de errores del lexer y el parser. Las
funcionalidades 1–3 y la UI se agregan encima de esto.

## Cómo ejecutar

```bash
python parser.py pruebas/errores.txt            # pregunta consola / archivo
python parser.py pruebas/errores.txt --consola
python parser.py archivo.txt --guardar          # escribe ParserOutput.txt
python lexer.py archivo.txt                     # solo tokens (Avance 2)
python -m unittest discover -s tests -v         # pruebas (40)
```

Código de salida: `0` si el archivo es correcto, `1` si tiene errores.

## Qué cambió

| Problema en el Avance 4 | Solución |
|---|---|
| El peer AS podía estar en cualquier posición del AS path | Debe ser el **primero** (`as_numbers[0]`; si el primer elemento es un `{...}`, debe estar dentro) |
| Los saltos de línea se ignoraban: un registro partido en 2 líneas, o 2 en una, era válido | Token `NEWLINE` en la gramática |
| Un número de 11+ dígitos se partía en dos tokens y pasaba como dos AS | Una sola regla `\d+`; más de 10 dígitos es error léxico |
| Ceros a la izquierda (`053046`, `01.2.3.4`) se aceptaban | Error léxico |
| Un error léxico + el error sintáctico que causaba = reporte duplicado | El lexer devuelve `ILLEGAL`; se reporta una sola vez |
| `p_error` solo decía "Syntax error [Line N]" y PLY podía perder el resto del archivo | Recuperación con `error NEWLINE`; todos los errores salen en una pasada |
| Mensajes sin contexto | Línea, campo (nombre y número), lexema y qué se esperaba |
| Los errores se imprimían al vuelo | `errores.Colector`: lista de `Problema` que la consola o la UI consumen |
| Había dos copias del lexer (`lexer.py` y `parser.py`) | `parser.py` importa el de `lexer.py` |
| Archivo vacío / inexistente / carpeta / sin permiso | Se reportan como error de tipo `archivo`, sin excepciones |
| Recursión derecha en `archivo` | Recursión izquierda (pila constante) |

## Decisión: rango de la máscara

El enunciado dice 1–31, pero el archivo de ejemplo `prueba` tiene 7 líneas
`0.0.0.0/0` (rutas por defecto, válidas en CIDR) y /32 también es válido.

- **1–31**: sin comentarios.
- **0 y 32**: se aceptan con **advertencia**.
- **> 32**: error (no existe en IPv4).

Para la regla estricta del enunciado, poner `MASK_ESTRICTA = True` en
`parser.py`. **Confirmar con la profesora cuál prefiere.**

## Usar el resultado desde otro módulo (UI)

```python
import parser as P
res = P.parse_file("archivo.txt")      # o P.parse_text(str)
res.ok                                  # True si no hay errores
res.colector.errores                    # lista de Problema
res.colector.advertencias
res.records, res.routing_table, res.all_as_numbers, res.as_graph
```

Cada `Problema` tiene: `linea`, `tipo` (léxico / sintáctico / semántico /
archivo), `severidad`, `campo`, `lexema`, `mensaje`.

## Pendiente (no incluido aquí)

Aristas repetidas por AS prepending (`3356 3356`), tratamiento de `AS_SET` en
el grafo, estructuras para las funcionalidades 2 y 3, y la UI.
