# Avance 3 — Analizador Léxico y Sintáctico para archivos MRT (TABLE_DUMP2)

**Curso:** C1-0124 Computabilidad y Complejidad

**Estudiantes:** Isaac Araya, Gabriel Coto y May Retana

## Descripción general

Este avance corresponde a la construcción de un **analizador léxico y sintáctico** para registros en formato **MRT `TABLE_DUMP2`**, el formato estándar usado para volcados de tablas de enrutamiento BGP (Border Gateway Protocol). El objetivo es reconocer y validar la estructura de cada línea de un archivo de este tipo, verificando que cumpla con la gramática formal definida para el proyecto.

El desarrollo se implementó en Python utilizando **PLY (Python Lex-Yacc)**, biblioteca que permite construir analizadores léxicos (`lex`) y sintácticos (`yacc`) de forma declarativa.

## Gramática formal

Se definió la gramática G = {V, T, A, S}:

- **Variables (no terminales):** `ARCHIVO`, `LINEA`, `PREFIX`, `AS_PATH`, `AS_ELEMENT`, `AS_SET`, `AS_SET_LIST`
- **Terminales:** `RECORD_TYPE`, `PIPE`, `STATE`, `IPADDR`, `SLASH`, `TIMESTAMP`, `PEER_AS`, `MASK`, `AS_PATH_NUM`, `LBRACE`, `RBRACE`, `COMMA`
- **Símbolo inicial:** `ARCHIVO`

Producciones principales:

```
ARCHIVO      → LINEA | LINEA ARCHIVO
LINEA        → RECORD_TYPE PIPE TIMESTAMP PIPE STATE PIPE IPADDR PIPE PEER_AS PIPE PREFIX PIPE AS_PATH
PREFIX       → IPADDR SLASH MASK
AS_PATH      → AS_ELEMENT | AS_ELEMENT AS_PATH
AS_ELEMENT   → AS_PATH_NUM | AS_SET
AS_SET       → LBRACE AS_SET_LIST RBRACE
AS_SET_LIST  → AS_PATH_NUM | AS_PATH_NUM COMMA AS_SET_LIST
```

Cada línea representa un registro con: tipo de registro, marca de tiempo, estado del anuncio (B/A/W), IP del peer, AS del peer, prefijo anunciado (IP/máscara) y la ruta de sistemas autónomos (AS Path), que puede incluir conjuntos de AS entre llaves.

Documento completo de referencia: `Gramatica_Proyecto_1.pdf`.

## Componentes del avance

| Archivo | Descripción |
|---|---|
| `lexer.py` | Analizador léxico independiente. Reconoce los tokens del lenguaje (`RECORD_TYPE`, `TIMESTAMP`, `STATE`, `IPADDR`, `PIPE`, `SLASH`, `NUMBER`, `LBRACE`, `RBRACE`, `COMMA`) y valida rangos (timestamps y números como enteros de 32 bits, máscaras entre 0 y 32, octetos de IP entre 0 y 255). Reporta errores léxicos indicando la línea y el lexema inválido. Puede ejecutarse de forma independiente sobre un archivo MRT y mostrar o guardar los tokens generados. |
| `parser.py` | Analizador léxico-sintáctico completo. Incluye su propia copia del lexer y añade las reglas gramaticales (`archivo`, `linea`, `prefix`, `as_path`, `as_set`, `as_set_list`) usando `ply.yacc`, construyendo así el parser LALR de la gramática definida. Reporta errores sintácticos con la línea y el token que los provoca. |
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
# Analizar solo los tokens de un archivo MRT
python lexer.py <archivo_mrt>

# Ejecutar el analizador léxico-sintáctico completo
python parser.py
```
