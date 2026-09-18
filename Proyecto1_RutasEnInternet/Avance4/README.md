# Avance 4 — Creación dinámica de estructuras de datos para archivos MRT (TABLE_DUMP2)

**Curso:** C1-0124 Computabilidad y Complejidad

**Estudiantes:** Isaac Araya, Gabriel Coto y May Retana

## Descripción general

Este avance parte del analizador léxico y sintáctico construido en el Avance 3 para registros en formato **MRT `TABLE_DUMP2`** (el formato estándar usado para volcados de tablas de enrutamiento BGP), y le agrega la **creación dinámica de los objetos y estructuras de datos** en las que queda almacenada la información conforme se va parseando cada línea, tal como pide el entregable 4 del enunciado.

El desarrollo se implementó en Python utilizando **PLY (Python Lex-Yacc)**, biblioteca que permite construir analizadores léxicos (`lex`) y sintácticos (`yacc`) de forma declarativa.

## Estructuras de datos construidas dinámicamente

Cada vez que la acción semántica de la regla `linea` se dispara (es decir, cada vez que se reconoce un registro `TABLE_DUMP2` completo y sintácticamente correcto), `parser.py` alimenta las siguientes estructuras globales:

| Estructura | Tipo | Para qué sirve |
|---|---|---|
| `records` | `list[dict]` | Guarda cada registro tal como fue parseado, en el orden de llegada. Sirve como bitácora completa y como base para recorrer secuencialmente el archivo. |
| `routing_table` | `dict[str, list[dict]]` (prefijo → lista de registros) | Permite, en O(1) promedio, obtener todos los registros que anuncian un prefijo dado. Es la estructura clave para la funcionalidad de detectar prefijos con más de un AS de origen (posible *prefix hijacking*), ya que evita recorrer todo `records` cada vez. |
| `all_as_numbers` | `set[int]` | Conjunto de todos los números de AS vistos (como peer o como parte de algún AS_PATH), sin duplicados, para consultas rápidas de pertenencia. |
| `as_graph` (clase `ASGraph`) | `dict[int, set[int]]` (lista de adyacencia) | Modela la topología de Internet implícita en los AS_PATH: cada AS_PATH aporta aristas entre AS consecutivos. Un grafo con lista de adyacencia permite responder eficientemente "¿cuáles son los vecinos de este AS?" (funcionalidad 2 del enunciado) y es la base natural para, más adelante, buscar todas las rutas entre dos AS (funcionalidad 3), sin tener que recorrer linealmente todos los registros. |

Estas cuatro estructuras se llenan directamente en las acciones de la gramática (no en un paso posterior de post-procesamiento), cumpliendo con lo pedido para este avance. Al final de la ejecución, `parser.py` imprime un resumen con la cantidad de elementos en cada una.

Se probó el parser contra el archivo de ejemplo grande (`prueba`, 500 000 líneas): corre en ~30 segundos, sin errores léxicos ni sintácticos, y produce 500 000 registros, 46 962 prefijos distintos, 5 876 AS distintos y un grafo de 5 876 nodos con 13 939 aristas.

## Gramática formal

Se definió la gramática G = {V, T, A, S}. A partir del Avance 3, el lexer ya **no** emite tokens `TIMESTAMP`/`PEER_AS`/`MASK`/`AS_PATH_NUM` distintos, porque eso generaba una ambigüedad real (un timestamp y un Peer AS pueden tener ambos 10 dígitos y el lexer no sabe en qué campo de la línea está). En su lugar, el lexer solo clasifica los números por cantidad de dígitos (`NUM10` = exactamente 10 dígitos, `NUM9` = de 1 a 9 dígitos) y es la **gramática** la que decide el significado de cada uno según la posición en que aparece:

- **Variables (no terminales, en minúscula):** `archivo`, `linea`, `timestamp`, `peer_as`, `prefix`, `mask`, `as_path`, `as_element`, `as_num`, `as_set`, `as_set_list`
- **Terminales:** `RECORD_TYPE`, `PIPE`, `STATE`, `IPADDR`, `SLASH`, `NUM10`, `NUM9`, `LBRACE`, `RBRACE`, `COMMA`
- **Símbolo inicial:** `archivo`

Producciones principales (ver `gramatica.md` para el detalle completo):

```
archivo      → linea archivo | linea
linea        → RECORD_TYPE PIPE timestamp PIPE STATE PIPE IPADDR PIPE
               peer_as PIPE prefix PIPE as_path
timestamp    → NUM10
peer_as      → NUM10 | NUM9
prefix       → IPADDR SLASH mask
mask         → NUM9
as_path      → as_element as_path | as_element
as_element   → as_num | as_set
as_num       → NUM10 | NUM9
as_set       → LBRACE as_set_list RBRACE
as_set_list  → as_num COMMA as_set_list | as_num
```

Cada línea representa un registro con: tipo de registro, marca de tiempo, estado del anuncio (B/A/W), IP del peer, AS del peer, prefijo anunciado (IP/máscara) y la ruta de sistemas autónomos (AS Path), que puede incluir conjuntos de AS entre llaves. Además, la acción de `linea` valida semánticamente que el `peer_as` reportado aparezca dentro del `as_path` de esa línea.

Documento de referencia del enunciado original: `Gramatica_Proyecto_1.pdf` (nota: ese PDF todavía usa los nombres de terminal `TIMESTAMP`/`PEER_AS`/`MASK`/`AS_PATH_NUM`; la gramática implementada los reemplazó por `NUM10`/`NUM9` para resolver la ambigüedad explicada arriba — ver `gramatica.md` para la versión actualizada).

## Componentes del avance

| Archivo | Descripción |
|---|---|
| `lexer.py` | Analizador léxico independiente. Reconoce los tokens del lenguaje (`RECORD_TYPE`, `STATE`, `IPADDR`, `PIPE`, `SLASH`, `NUM10`, `NUM9`, `LBRACE`, `RBRACE`, `COMMA`) y valida rangos (números de 10 dígitos como enteros de 32 bits, octetos de IP entre 0 y 255). Reporta errores léxicos indicando la línea y el lexema inválido. Puede ejecutarse de forma independiente sobre un archivo MRT y mostrar o guardar los tokens generados. |
| `parser.py` | Analizador léxico-sintáctico completo, con creación dinámica de estructuras. Incluye su propia copia del lexer y añade las reglas gramaticales (`archivo`, `linea`, `prefix`, `as_path`, `as_element`, `as_set`, `as_set_list`) usando `ply.yacc`, construyendo así el parser LALR de la gramática definida. Las acciones semánticas también alimentan `records`, `routing_table`, `all_as_numbers` y `as_graph` (ver sección anterior). Reporta errores léxicos, sintácticos y un error semántico (PEER_AS que no aparece como primer elemento del AS_PATH). No imprime el listado de tokens: solo indica si el archivo tiene tokens/sintaxis correctos y muestra el resumen de las estructuras construidas — eso mantiene la salida legible incluso en archivos de cientos de miles de líneas. |
| `calculadora_analizador_sintactico.py` | Versión de prueba/depuración que valida por partes una línea de forma interactiva (símbolo inicial parcial `linea_inicio`), útil para verificar el reconocimiento incremental de los primeros campos de un registro y la validación del prefijo. |
| `gramatica.md` | Especificación formal de la gramática (variables, terminales, símbolo inicial y producciones). |
| `Gramatica_Proyecto_1.pdf` | Documento del enunciado/definición de la gramática del proyecto. |
| `parser.out` | Salida generada automáticamente por PLY con la tabla de estados LALR del parser (útil para depurar conflictos de la gramática). |
| `prueba` | Archivo de ejemplo con una línea en formato `TABLE_DUMP2` para probar el analizador. |
| `ply/` | Biblioteca de terceros PLY (Python Lex-Yacc), utilizada como dependencia para construir el lexer y el parser. |

## Ejemplo de entrada

```
TABLE_DUMP2|1785888000|B|200.40.162.202|6057|83.135.64.0/19|6057 8881
```

Este registro es reconocido como: tipo `TABLE_DUMP2`, timestamp `1785888000`, estado `B` (Best/Announcement), IP del peer `200.40.162.202`, AS del peer `6057`, prefijo `83.135.64.0/19` y AS Path `6057 8881`.

## Manejo de errores

El analizador distingue dos niveles de error:

- **Errores léxicos:** tokens fuera de rango o inválidos (timestamps/números mayores a `2^32 - 1`, máscaras fuera de 0-32, IPs con octetos inválidos, caracteres no reconocidos).
- **Errores sintácticos:** secuencias de tokens que no respetan la estructura definida por la gramática (por ejemplo, campos faltantes o en orden incorrecto).

En ambos casos se reporta el número de línea y el fragmento o token que originó el error.

## Cómo ejecutar

Requiere Python 3 y la biblioteca PLY (incluida en la carpeta `ply/`).

```bash
# Analizar solo los tokens de un archivo MRT (herramienta independiente
# del Avance 2, sigue imprimiendo los tokens)
python lexer.py <archivo_mrt>

# Ejecutar el analizador léxico-sintáctico completo (parsea, valida y
# construye records / routing_table / all_as_numbers / as_graph).
# No imprime tokens: solo el estado léxico/sintáctico y el resumen de
# las estructuras dinámicas.
python parser.py <archivo_mrt>
```
