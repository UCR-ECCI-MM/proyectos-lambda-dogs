# Avance 5 — Aplicación completa (errores + funcionalidades 1-3 + GUI)

**Curso:** CI0124 Computabilidad y Complejidad · **Proyecto 1:** Rutas en Internet

Este avance rehace el manejo de errores del lexer y el parser y agrega las
funcionalidades 1–3 de la sección 4 del enunciado, con GUI (Raylib) y consola.

## Cómo ejecutar

```bash
python parser.py pruebas/errores.txt            # pregunta consola / archivo
python parser.py pruebas/errores.txt --consola
python parser.py archivo.txt --guardar          # escribe ParserOutput.txt
python lexer.py archivo.txt                     # solo tokens (Avance 2)
python -m unittest discover -s tests -v         # pruebas

pip install raylib                              # solo para la GUI
python GUI.py [archivo.txt]                     # aplicación gráfica
python consola.py archivo.txt                   # menú de consola (respaldo)
python consola.py archivo.txt --origenes        # funcionalidad 1
python consola.py archivo.txt --as 53046        # funcionalidad 2
python consola.py archivo.txt --rutas 7.0.0.0/8 8.8.8.0/24   # funcionalidad 3
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

## Funcionalidades (analysis.py)

Los índices se llenan **durante el parseo** (`p_linea` llama a
`res.index.add(...)`), así que ninguna consulta recorre la lista de registros.

1. **Orígenes distintos por prefijo:** `index.origins[prefijo][AS origen]`;
   `index.conflicts` es el conjunto de prefijos con más de un origen. El
   origen es el último AS del path (si es un `{...}`, todos sus miembros).
2. **Aristas de un AS:** `index.by_peer[peer AS][IP del peer]` -> prefijos y
   AS path (dos lookups en dict). Un AS que solo aparece dentro de paths (no en
   el campo 5) no tiene aristas propias y se informa así.
3. **Rutas entre dos prefijos:** se toman los AS origen de A y de B
   (`origins_for`) y se enumeran **todas las rutas simples** (sin repetir AS)
   entre ellos en el grafo AS-AS (DFS iterativo con poda por BFS). Límites:
   12 AS por ruta y 1000 rutas. **Es una interpretación del enunciado:
   confirmar con la profesora.**

El AS prepending (`3356 3356`) ya no crea auto-aristas en el grafo.

## Archivos de prueba

`pruebas/ejemplo_completo.txt` (10 líneas, un prefijo con dos orígenes),
`pruebas/errores.txt` (errores léxicos/sintácticos/semánticos),
`pruebas/prueba_corta.txt`.
