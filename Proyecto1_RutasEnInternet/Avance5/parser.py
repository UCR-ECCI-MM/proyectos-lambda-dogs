"""
Analizador sintáctico del dump MRT (TABLE_DUMP2) + creación dinámica de
estructuras.

Cambios del Avance 5 (detección de errores):
  * Una línea = un registro (token NEWLINE en la gramática).
  * Recuperación de errores con el token `error` de PLY: una línea mala se
    descarta y el análisis continúa, así se reportan TODOS los errores.
  * Los errores se acumulan en un Colector (errores.py), con línea, campo,
    lexema y mensaje; nada se imprime al vuelo.
  * Validaciones semánticas: el AS path debe COMENZAR con el peer AS, y el
    rango de la máscara.
  * Archivo vacío / inexistente / ilegible se reportan como errores.
  * parse_file() / parse_text() devuelven un ParseResult sin estado global
    para que la consola o la UI lo consuman.
"""

import os
import sys
import argparse
from dataclasses import dataclass, field

import ply.yacc as yacc

from lexer import tokens, lexer as _ply_lexer, MRTLexer, FIELDS   # noqa: F401
from errores import Colector, LEXICO, SINTACTICO, SEMANTICO, ARCHIVO
from display import (C, strip_ansi, render_structures_report,
                      render_problemas)

# ---------------------------------------------------------------------------
# Regla para la máscara del prefijo.
#
# El enunciado dice "un número entre 1 y 31", pero:
#   * el archivo de ejemplo `prueba` contiene líneas con /0 (rutas por
#     defecto, 0.0.0.0/0) y es CIDR válido;
#   * /32 (host) también es CIDR válido.
# DECISIÓN: 1-31 se acepta sin comentarios; 0 y 32 se aceptan pero generan
# una ADVERTENCIA (se salen de lo que dice el enunciado); más de 32 es ERROR
# (no existe en IPv4). Para volver a la regla estricta del enunciado, poner
# MASK_ESTRICTA = True (entonces 0 y 32 son error).
# ---------------------------------------------------------------------------
MASK_MIN = 1
MASK_MAX = 31
MASK_CIDR_MAX = 32
MASK_ESTRICTA = False


# ---------------------------------------------------------------------------
# Estructuras de datos
# ---------------------------------------------------------------------------

class ASGraph:

    def __init__(self):
        self.adjacency = {}  # dict: número de AS -> set de AS vecinos

    def add_node(self, as_number):
        self.adjacency.setdefault(as_number, set())

    def add_edge(self, as1, as2):
        self.add_node(as1)
        self.add_node(as2)
        self.adjacency[as1].add(as2)
        self.adjacency[as2].add(as1)

    def nodes(self):
        return set(self.adjacency.keys())

    def edges(self):
        seen = set()
        result = []
        for a, neighbors in self.adjacency.items():
            for b in neighbors:
                if (b, a) not in seen:
                    seen.add((a, b))
                    result.append((a, b))
        return result

    def degree(self, as_number):
        return len(self.adjacency.get(as_number, set()))


def flatten_as_path(as_path):
    flat = []
    for element in as_path:
        if isinstance(element, set):
            flat.extend(sorted(element))
        else:
            flat.append(element)
    return flat


@dataclass
class ParseResult:
    records: list = field(default_factory=list)
    routing_table: dict = field(default_factory=dict)
    all_as_numbers: set = field(default_factory=set)
    as_graph: ASGraph = field(default_factory=ASGraph)
    colector: Colector = field(default_factory=Colector)
    total_lines: int = 0

    @property
    def ok(self):
        """True si el archivo no tiene ningún error (las advertencias no
        cuentan)."""
        return not self.colector.errores


# Resultado que las acciones de la gramática van llenando
_res = None


# ---------------------------------------------------------------------------
# Gramática. Convención: MAYÚSCULAS solo para terminales (tokens);
# variables en minúscula.
# ---------------------------------------------------------------------------

start = 'archivo'


def p_archivo(p):
    'archivo : INICIO lista'
    p[0] = None


# Recursión por la izquierda: la pila del parser no crece con el número de
# líneas (con recursión derecha crecía hasta 500 000 entradas).
def p_lista_multiple(p):
    'lista : lista item'
    p[0] = None


def p_lista_single(p):
    'lista : item'
    p[0] = None


def p_item_linea(p):
    'item : linea'
    p[0] = None


def p_item_error(p):
    'item : error NEWLINE'
    # Línea descartada (ya se reportó en p_error o por el lexer). errok()
    # saca a PLY del modo de recuperación para que un error en la línea
    # SIGUIENTE también se reporte (si no, PLY silencia 3 tokens).
    parser.errok()
    p[0] = None


def p_linea(p):
    ('linea : RECORD_TYPE PIPE timestamp PIPE STATE PIPE IPADDR PIPE '
     'peer_as PIPE prefix PIPE as_path NEWLINE')

    line = p.slice[1].lineno
    timestamp = p[3]
    state = p[5]
    peer_ip = p[7]
    peer_as = p[9]
    prefix = p[11]
    as_path = p[13]
    col = _res.colector
    hay_error = False

    # --- El AS path debe COMENZAR con el peer AS (enunciado, campo 7) ----
    first = as_path[0]
    if isinstance(first, set):
        comienza_bien = peer_as in first
        first_txt = '{' + ','.join(str(n) for n in sorted(first)) + '}'
    else:
        comienza_bien = (first == peer_as)
        first_txt = str(first)
    if not comienza_bien:
        col.error(
            line, SEMANTICO,
            f"el AS path debe comenzar con el peer AS ({peer_as}), pero "
            f"comienza con {first_txt}",
            campo='AS path', lexema=first_txt)
        hay_error = True

    # --- Rango de la máscara ---------------------------------------------
    mask = prefix['mask']
    prefix_txt = f"{prefix['ip']}/{mask}"
    if mask > MASK_CIDR_MAX:
        col.error(
            line, SEMANTICO,
            f"máscara fuera de rango: {mask} (el máximo en IPv4 es "
            f"{MASK_CIDR_MAX})",
            campo='prefijo destino', lexema=prefix_txt)
        hay_error = True
    elif not (MASK_MIN <= mask <= MASK_MAX):
        if MASK_ESTRICTA:
            col.error(
                line, SEMANTICO,
                f"máscara {mask} fuera del rango {MASK_MIN}-{MASK_MAX} "
                f"del enunciado",
                campo='prefijo destino', lexema=prefix_txt)
            hay_error = True
        else:
            col.advertencia(
                line, SEMANTICO,
                f"máscara {mask} fuera del rango {MASK_MIN}-{MASK_MAX} del "
                f"enunciado (válida en CIDR; se acepta)",
                campo='prefijo destino', lexema=prefix_txt)

    if hay_error:
        p[0] = None
        return

    # --- Registro válido: se crean las estructuras dinámicamente ---------
    as_numbers = flatten_as_path(as_path)
    record = {
        'record_type': p[1],
        'timestamp': timestamp,
        'state': state,
        'peer_ip': peer_ip,
        'peer_as': peer_as,
        'prefix': prefix,
        'as_path': as_path,
        'line': line,
    }
    _res.records.append(record)                                  # list
    _res.routing_table.setdefault(prefix_txt, []).append(record)  # dict
    _res.all_as_numbers.update(as_numbers)                       # set
    _res.all_as_numbers.add(peer_as)
    for left, right in zip(as_numbers, as_numbers[1:]):          # grafo
        _res.as_graph.add_edge(left, right)
    if as_numbers:
        _res.as_graph.add_node(as_numbers[0])

    p[0] = record


def p_timestamp(p):
    'timestamp : NUM10'
    p[0] = p[1]


def p_peer_as_10(p):
    'peer_as : NUM10'
    p[0] = p[1]


def p_peer_as_9(p):
    'peer_as : NUM9'
    p[0] = p[1]


def p_prefix(p):
    'prefix : IPADDR SLASH mask'
    p[0] = {'ip': p[1], 'mask': p[3]}


# La máscara cabe en 9 dígitos. El rango se valida en p_linea.
def p_mask(p):
    'mask : NUM9'
    p[0] = p[1]


def p_as_path_multiple(p):
    'as_path : as_element as_path'
    p[0] = p[1] + p[2]


def p_as_path_single(p):
    'as_path : as_element'
    p[0] = p[1]


def p_as_element_num(p):
    'as_element : as_num'
    p[0] = [p[1]]


def p_as_element_set(p):
    'as_element : as_set'
    p[0] = [p[1]]


def p_as_num_10(p):
    'as_num : NUM10'
    p[0] = p[1]


def p_as_num_9(p):
    'as_num : NUM9'
    p[0] = p[1]


def p_as_set(p):
    'as_set : LBRACE as_set_list RBRACE'
    p[0] = set(p[2])


def p_as_set_list_multiple(p):
    'as_set_list : as_num COMMA as_set_list'
    p[0] = [p[1]] + p[3]


def p_as_set_list_single(p):
    'as_set_list : as_num'
    p[0] = [p[1]]


# ---------------------------------------------------------------------------
# Errores sintácticos
# ---------------------------------------------------------------------------

_NOMBRE_TOKEN = {
    'RECORD_TYPE': "'TABLE_DUMP2'",
    'STATE': "'B', 'A' o 'W'",
    'IPADDR': 'una dirección IP',
    'PIPE': "'|'",
    'SLASH': "'/'",
    'LBRACE': "'{'",
    'RBRACE': "'}'",
    'COMMA': "','",
    'NEWLINE': 'fin de línea',
}


def _describir_esperado(nombres):
    """Convierte el conjunto de terminales esperados en texto legible."""
    nums = {n for n in nombres if n in ('NUM10', 'NUM9')}
    otros = sorted(_NOMBRE_TOKEN[n] for n in nombres if n in _NOMBRE_TOKEN)
    partes = []
    if nums == {'NUM10'}:
        partes.append('un número de exactamente 10 dígitos')
    elif nums == {'NUM9'}:
        partes.append('un número de 1 a 9 dígitos')
    elif nums:
        partes.append('un número')
    partes += otros
    if not partes:
        return 'otra cosa'
    if len(partes) == 1:
        return partes[0]
    return ', '.join(partes[:-1]) + ' o ' + partes[-1]


def _lexema_de(tok):
    if tok.type == 'NEWLINE':
        return '<fin de línea>'
    return str(tok.value)


def p_error(tok):
    col = _res.colector

    if tok is None:
        # No debería pasar (el lexer siempre cierra con NEWLINE), pero por si
        # acaso el archivo termina en medio de una estructura.
        col.error(_res.total_lines, SINTACTICO,
                  'fin de archivo inesperado')
        return

    # El lexer ya reportó este problema; no se duplica.
    if tok.type == 'ILLEGAL' or tok.lineno in col.lineas_con_error_lexico:
        return

    idx = tok.field
    campo = f"{min(idx, 6) + 1} ({FIELDS[min(idx, 6)]})"
    lexema = _lexema_de(tok)

    if tok.type == 'PIPE' and idx >= 6:
        col.error(tok.lineno, SINTACTICO,
                  'la línea tiene más de 7 campos (hay un "|" de más)',
                  campo=campo, lexema=lexema)
        return

    esperados = {
        t for t in parser.action.get(parser.statestack[-1], {})
        if t not in ('error', '$end')
    }
    # Los estados LALR mezclan contextos (AS path vs. dentro de un AS_SET),
    # así que se filtran los terminales que no aplican al contexto actual.
    dentro_de_set = any(getattr(s, 'type', None) == 'LBRACE'
                        for s in parser.symstack)
    if dentro_de_set:
        esperados -= {'NEWLINE', 'LBRACE'}
    else:
        esperados -= {'COMMA', 'RBRACE'}
    esperado = _describir_esperado(esperados)

    if tok.type == 'NEWLINE':
        if idx < 6:
            msg = (f"fin de línea inesperado: la línea solo tiene "
                   f"{idx + 1} de 7 campos; se esperaba {esperado}")
        else:
            msg = f"fin de línea inesperado; se esperaba {esperado}"
    else:
        msg = f"se esperaba {esperado}"

    col.error(tok.lineno, SINTACTICO, msg, campo=campo, lexema=lexema)


# yacc.yacc() solo para construir las tablas; los warnings por el token
# ILLEGAL "sin usar" son esperados (nunca aparece en la gramática a propósito).
parser = yacc.yacc(debug=False, write_tables=False,
                   errorlog=yacc.NullLogger())


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def parse_text(data):
    """Analiza el contenido (str) de un dump MRT y devuelve un ParseResult."""
    global _res
    res = ParseResult()
    _res = res
    col = res.colector

    if not data.strip():
        col.error(0, ARCHIVO, 'el archivo está vacío (no tiene registros)')
        return res

    res.total_lines = data.count('\n') + (0 if data.endswith('\n') else 1)

    def on_illegal(tok):
        col.error(tok.lineno, LEXICO, tok.reason,
                  campo=f"{min(tok.field, 6) + 1} ({FIELDS[min(tok.field, 6)]})",
                  lexema=tok.value)
        col.lineas_con_error_lexico.add(tok.lineno)

    mrt_lexer = MRTLexer(_ply_lexer, on_illegal=on_illegal)
    parser.parse(data, lexer=mrt_lexer)
    return res


def parse_file(path):
    """Lee y analiza un archivo. Nunca lanza excepciones por problemas del
    archivo: los reporta como errores en el resultado."""
    global _res
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            data = f.read()
    except FileNotFoundError:
        msg = f"el archivo no existe: {path}"
    except IsADirectoryError:
        msg = f"la ruta es una carpeta, no un archivo: {path}"
    except PermissionError:
        msg = f"no hay permiso para leer el archivo: {path}"
    except OSError as e:
        msg = f"no se pudo leer el archivo ({e.strerror or e}): {path}"
    else:
        return parse_text(data)

    res = ParseResult()
    res.colector.error(0, ARCHIVO, msg)
    _res = res
    return res


# ---------------------------------------------------------------------------
# Reporte de consola
# ---------------------------------------------------------------------------

def build_report(res):
    """Arma el reporte completo (lista de líneas de texto)."""
    col = res.colector
    err_lex = any(e.tipo == LEXICO for e in col.errores)
    err_sin = any(e.tipo == SINTACTICO for e in col.errores)
    err_sem = any(e.tipo == SEMANTICO for e in col.errores)
    err_arc = any(e.tipo == ARCHIVO for e in col.errores)

    lines = []
    if err_arc:
        lines.append(f"{C.RED}✗ No se pudo analizar el archivo{C.RESET}")
    else:
        for nombre, bien, mal, hay in (
                ("tokens", "CORRECTOS", "INCORRECTOS", err_lex),
                ("sintaxis", "CORRECTA", "INCORRECTA", err_sin),
                ("semántica", "CORRECTA", "INCORRECTA", err_sem)):
            if hay:
                lines.append(f"{C.RED}✗ Archivo MRT con {nombre} "
                             f"{mal}{C.RESET}")
            else:
                lines.append(f"{C.GREEN}✓ Archivo MRT con {nombre} "
                             f"{bien}{C.RESET}")
    lines.append("")
    lines += render_problemas(col)

    if res.ok:
        lines.append("")
        lines += render_structures_report(
            res.records, res.routing_table, res.all_as_numbers,
            res.as_graph, flatten_as_path)
    else:
        lines.append("")
        lines.append(f"{C.DIM}Corrija los errores para ver el análisis "
                     f"del archivo.{C.RESET}")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Analiza un archivo dump MRT (TABLE_DUMP2).")
    ap.add_argument("archivo", help="ruta del archivo MRT")
    destino = ap.add_mutually_exclusive_group()
    destino.add_argument("--consola", action="store_true",
                         help="mostrar el resultado en consola")
    destino.add_argument("--guardar", action="store_true",
                         help="guardar el resultado en ParserOutput.txt")
    args = ap.parse_args(argv)

    if args.guardar:
        choice = 'F'
    elif args.consola or not sys.stdin.isatty():
        choice = 'C'
    else:
        choice = input("Mostrar resultados en (C)onsola o guardarlos en "
                       "un (F)ile? [C/F]: ").strip().upper()

    res = parse_file(args.archivo)
    output = "\n".join(build_report(res)) + "\n"

    if choice == 'F':
        with open("ParserOutput.txt", "w", encoding="utf-8") as out_file:
            out_file.write(strip_ansi(output))
        print("Resultados guardados en ParserOutput.txt")
    else:
        print(output, end="")

    return 0 if res.ok else 1


if __name__ == '__main__':
    sys.exit(main())
