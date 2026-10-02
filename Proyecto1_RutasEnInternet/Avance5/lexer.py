"""
Analizador léxico del dump MRT (TABLE_DUMP2).

Este es el ÚNICO lexer del proyecto: parser.py lo importa (antes había una
copia duplicada en cada archivo).

Cambios del Avance 5:
  * NEWLINE es un token: una línea = un registro.
  * Los lexemas inválidos ya no se descartan: se devuelven como token
    ILLEGAL (con el motivo en `reason`). Así el parser descarta la línea
    completa y se reporta un solo error por problema, en vez de que el
    parser vea un token "faltante" y duplique el reporte.
  * Los números se leen con una sola regla (\\d+), así un número de 11 o más
    dígitos es un error (antes se partía silenciosamente en dos tokens).
  * Los números con ceros a la izquierda y las IP mal formadas se reportan.
"""

import sys
import re
import ply.lex as lex

tokens = (
    'RECORD_TYPE',
    'STATE',
    'IPADDR',
    'PIPE',
    'SLASH',
    'NUM10',
    'NUM9',
    'LBRACE',
    'RBRACE',
    'COMMA',
    'NEWLINE',
    'INICIO',    # token sintético que el MRTLexer emite al comenzar
    'ILLEGAL',   # lexema inválido; nunca aparece en la gramática
)

# Nombres de los 7 campos de una línea, en orden (índice = # de '|' vistos)
FIELDS = (
    'record type',
    'timestamp',
    'state',
    'peer IP',
    'peer AS',
    'prefijo destino',
    'AS path',
)

MAX_UINT32 = 2**32 - 1


def _illegal(t, reason, value=None):
    """Convierte el token actual en un ILLEGAL con su motivo."""
    t.type = 'ILLEGAL'
    t.reason = reason
    if value is not None:
        t.value = value
    return t


def t_RECORD_TYPE(t):
    r'TABLE_DUMP2\b'
    return t


def t_STATE(t):
    r'[BAW]\b'
    return t


OCTET = r'(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)'


@lex.TOKEN(r'\b(' + OCTET + r'\.){3}' + OCTET + r'(?![\d.])')
def t_IPADDR(t):
    return t


# Algo con forma de IP (dígitos separados por puntos) que NO es una IP
# válida: octeto > 255, ceros a la izquierda, cantidad de octetos distinta
# de 4, etc. Va después de t_IPADDR para que las IP válidas ganen.
def t_BADIP(t):
    r'\d+(\.\d+)+\.?'
    return _illegal(
        t, 'dirección IP inválida (deben ser 4 octetos de 0 a 255, '
           'sin ceros a la izquierda)')


t_PIPE = r'\|'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_COMMA = r','
t_SLASH = r'/'


# Todo número se lee completo y se clasifica por cantidad de dígitos
# (NUM10 = exactamente 10, NUM9 = de 1 a 9). Qué significa cada uno
# (timestamp, peer AS, máscara, AS del path) lo decide la gramática.
def t_NUMBER(t):
    r'\d+'
    text = t.value
    if len(text) > 1 and text[0] == '0':
        return _illegal(t, 'número con ceros a la izquierda')
    if len(text) > 10:
        return _illegal(t, f'número de {len(text)} dígitos (máximo 10)')
    value = int(text)
    if len(text) == 10:
        if value > MAX_UINT32:
            return _illegal(
                t, f'número fuera del rango de 32 bits (máx. {MAX_UINT32})')
        t.type = 'NUM10'
    else:
        t.type = 'NUM9'
    t.value = value
    return t


# Un salto de línea (o varios seguidos) termina un registro
def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    return t


# Espacios, tabs y retornos de carro no son tokens
t_ignore = ' \t\r'

_illegal_run = re.compile(r'[^\s|/{},]+')


def t_error(t):
    match = _illegal_run.match(t.value)
    bad = match.group(0) if match else t.value[0]
    tok = lex.LexToken()
    tok.type = 'ILLEGAL'
    tok.value = bad
    tok.lineno = t.lexer.lineno
    tok.lexpos = t.lexer.lexpos
    tok.reason = 'token no reconocido'
    t.lexer.skip(len(bad))
    return tok


lexer = lex.lex()


class MRTLexer:
    """
    Envoltorio sobre el lexer de PLY que:
      * lleva la cuenta de '|' de la línea actual y se la pone a cada token
        en `tok.field` (índice 0-6 del campo en que está el token), para
        poder decir en qué campo ocurrió un error;
      * ignora saltos de línea iniciales y consecutivos (líneas en blanco);
      * agrega un NEWLINE final si el archivo no termina en salto de línea;
      * emite un token sintético INICIO al comenzar. Sin él, si el primer
        token del archivo es inválido la pila de PLY tiene un solo estado y
        PLY descarta el token sin usar la regla `error` (y se pierde el
        reporte de las líneas siguientes);
      * reporta los tokens ILLEGAL como errores léxicos al colector.

    Cumple la interfaz que PLY exige a un lexer: input() y token().
    """

    def __init__(self, ply_lexer, on_illegal=None):
        self._lexer = ply_lexer
        self._on_illegal = on_illegal
        self.last_line = 1
        self._reset()

    def _reset(self):
        self._started = False
        self._pipes = 0
        self._last_type = 'NEWLINE'   # así se ignoran los saltos iniciales
        self.last_line = 1

    def input(self, data):
        self._lexer.lineno = 1
        self._lexer.input(data)
        self._reset()

    def token(self):
        if not self._started:
            self._started = True
            ini = lex.LexToken()
            ini.type = 'INICIO'
            ini.value = ''
            ini.lineno = 1
            ini.lexpos = 0
            ini.field = 0
            return ini

        while True:
            tok = self._lexer.token()

            if tok is None:
                if self._last_type != 'NEWLINE':
                    nl = lex.LexToken()
                    nl.type = 'NEWLINE'
                    nl.value = '\n'
                    nl.lineno = self._lexer.lineno
                    nl.lexpos = self._lexer.lexpos
                    nl.field = self._pipes
                    self._last_type = 'NEWLINE'
                    self._pipes = 0
                    return nl
                return None

            if tok.type == 'NEWLINE':
                if self._last_type == 'NEWLINE':
                    continue
                tok.field = self._pipes
                self._pipes = 0
                self._last_type = 'NEWLINE'
                self.last_line = tok.lineno
                return tok

            tok.field = self._pipes
            if tok.type == 'PIPE':
                self._pipes += 1
            self._last_type = tok.type
            self.last_line = tok.lineno

            if tok.type == 'ILLEGAL' and self._on_illegal is not None:
                self._on_illegal(tok)
            return tok


# Programa principal: lista los tokens de un archivo (Avance 2)
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python lexer.py <archivo_mrt>")
        sys.exit(1)

    found_illegal = []
    mrt = MRTLexer(lexer, on_illegal=found_illegal.append)
    with open(sys.argv[1], 'r', encoding='utf-8', errors='replace') as f:
        mrt.input(f.read())

    while True:
        tok = mrt.token()
        if tok is None:
            break
        print(tok)

    if found_illegal:
        for tok in found_illegal:
            print(f"Error léxico [línea {tok.lineno}] campo "
                  f"{tok.field + 1} ({FIELDS[min(tok.field, 6)]}): "
                  f"'{tok.value}' — {tok.reason}")
        print("Archivo MRT con tokens INCORRECTOS")
    else:
        print("Archivo MRT con tokens CORRECTOS :)")
