import sys
import re
import ply.lex as lex
import ply.yacc as yacc


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

# List of all token types that can be recognized by the lexer
tokens = (
    'RECORD_TYPE',
    'TIMESTAMP',
    'STATE',
    'IPADDR',
    'PIPE',
    'SLASH',
    'NUMBER',
    'LBRACE',
    'RBRACE',
    'COMMA',
)

# Maximum value for a 32-bit unsigned integer, used to validate both
# the TIMESTAMP token and the NUMBER token
MAX_UINT32 = 2**32 - 1


# Recognizes the TABLE_DUMP2 value used at the beginning of each record
def t_RECORD_TYPE(t):
    r'TABLE_DUMP2\b'
    return t


# Recognizes the possible states of a record: B, A or W
def t_STATE(t):
    r'[BAW]\b'
    return t


# Recognizes the timestamp field, which must have exactly 10 digits
# (unix timestamp). It must be defined before t_NUMBER so PLY gives it
# priority over the generic NUMBER rule.
def t_TIMESTAMP(t):
    r'(?<!\d)\d{10}(?!\d)'

    value = int(t.value)

    if value > MAX_UINT32:
        print(
            f"Lexical error [Line {t.lineno}]: "
            f"Timestamp out of the allowed range (32-bit uint): {value}"
        )
        t.lexer.has_errors = True
        return None

    t.value = value
    return t


# Recognizes IPv4 addresses and makes sure each octet is between 0 and 255
OCTET = r'(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)'


@lex.TOKEN(r'\b(' + OCTET + r'\.){3}' + OCTET + r'\b')
def t_IPADDR(t):
    return t


# Separators used between fields and between an address and its mask
t_PIPE = r'\|'


# Braces and commas used when an AS path contains a group of AS numbers
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_COMMA = r','


def t_SLASH(t):
    r'/'
    t.lexer.after_slash = True
    return t


def t_NUMBER(t):
    r'\d+'

    value = int(t.value)
    after_slash = getattr(t.lexer, 'after_slash', False)
    t.lexer.after_slash = False  # el flag solo aplica al número inmediatamente después del '/'

    if after_slash and value > 32:
        print(
            f"Lexical error [Line {t.lineno}]: "
            f"Mask out of range (0-32): {value}"
        )
        t.lexer.has_errors = True
        return None

    if value > MAX_UINT32:
        print(
            f"Lexical error [Line {t.lineno}]: "
            f"Number out of the allowed range (32-bit uint): {value}"
        )
        t.lexer.has_errors = True
        return None

    t.value = value
    return t


# Keeps track of line numbers when the lexer finds one or more newlines
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


# Spaces, tabs and carriage returns do not need to be returned as tokens
t_ignore = ' \t\r'


# Handles text that does not match any of the defined token rules
_illegal_run = re.compile(r'[^\s|/{},]+')


def t_error(t):
    # Try to report the whole invalid sequence instead of one character at a time
    match = _illegal_run.match(t.value)
    bad_lexeme = match.group(0) if match else t.value[0]

    print(
        f"Lexical error [Line {t.lineno}]: "
        f"Illegal token '{bad_lexeme}'"
    )

    t.lexer.has_errors = True
    t.lexer.skip(len(bad_lexeme))


lexer = lex.lex()


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def p_archivo_multiple(p):
    'archivo : linea archivo'
    p[0] = [p[1]] + p[2]

def p_archivo_single(p):
    'archivo : linea'
    p[0] = [p[1]]

def p_linea(p):
    ('linea : RECORD_TYPE PIPE TIMESTAMP PIPE STATE PIPE IPADDR PIPE '
     'NUMBER PIPE prefix PIPE as_path')
    p[0] = {
        'record_type': p[1],
        'timestamp': p[3],
        'state': p[5],
        'peer_ip': p[7],
        'peer_as': p[9],
        'prefix': p[11],
        'as_path': p[13],
    }

def p_prefix(p):
    'prefix : IPADDR SLASH NUMBER'
    p[0] = (p[1], p[3])

def p_as_path_multiple(p):
    'as_path : as_element as_path'
    p[0] = [p[1]] + p[2]

def p_as_path_single(p):
    'as_path : as_element'
    p[0] = [p[1]]

def p_as_set_list_multiple(p):
    'as_set_list : NUMBER COMMA as_set_list'
    p[0] = [p[1]] + p[3]


def p_as_set_list_single(p):
    'as_set_list : NUMBER'
    p[0] = [p[1]]

def p_error(p):
    if p is not None:
        print(
            f"Syntax error [Line {p.lineno}]: "
            f"invalid token '{p.value}'"
        )
    else:
        print("Syntax error: unexpected end of input")

    parser.has_errors = True

parser = yacc.yacc()