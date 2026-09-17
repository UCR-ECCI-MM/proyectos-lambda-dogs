import sys
import re
import ply.lex as lex
import ply.yacc as yacc


# ---------------------------------------------------------------------------
# Lexer
#
# The lexer doesn't know in which field of the line it is: it only classifies each
# sequence of digits by its length. All the ambiguity regarding Timestamp/Peer AS
# is resolved later, in the grammar (see p_timestamp and p_peer_as).
# ---------------------------------------------------------------------------

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
)

MAX_UINT32 = 2**32 - 1


def t_RECORD_TYPE(t):
    r'TABLE_DUMP2\b'
    return t


def t_STATE(t):
    r'[BAW]\b'
    return t


OCTET = r'(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)'


@lex.TOKEN(r'\b(' + OCTET + r'\.){3}' + OCTET + r'\b')
def t_IPADDR(t):
    return t


t_PIPE = r'\|'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_COMMA = r','
t_SLASH = r'/'


# Exactly 10 digits. Defined before t_NUM9 so it has priority.
def t_NUM10(t):
    r'\d{10}'

    value = int(t.value)
    if value > MAX_UINT32:
        print(
            f"Lexical error [Line {t.lineno}]: "
            f"Number out of the allowed range (32-bit uint): {value}"
        )
        t.lexer.has_errors = True
        return None

    t.value = value
    return t


# Numbers of 1 to 9 digits (never can exceed 2**32 - 1, so no range validation needed here)
def t_NUM9(t):
    r'\d{1,9}'
    t.value = int(t.value)
    return t


def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


t_ignore = ' \t\r'

_illegal_run = re.compile(r'[^\s|/{},]+')


def t_error(t):
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
#
# Convention: UPPERCASE only for terminals (tokens). The variables/non
# terminals (archivo, linea, timestamp, peer_as, prefix, mask, as_path,
# as_element, as_num, as_set, as_set_list) go in lowercase.
# ---------------------------------------------------------------------------

def p_archivo_multiple(p):
    'archivo : linea archivo'
    p[0] = None

def p_archivo_single(p):
    'archivo : linea'
    p[0] = None

def p_linea(p):
    ('linea : RECORD_TYPE PIPE timestamp PIPE STATE PIPE IPADDR PIPE '
     'peer_as PIPE prefix PIPE as_path')

    peer_as = p[9]
    as_numbers = p[13]

    if peer_as not in as_numbers:
        print(
            f"Semantic error [Line {p.lineno(1)}]: "
            f"PEER_AS ({peer_as}) does not appear in AS_PATH {sorted(as_numbers)}"
        )
        parser.has_errors = True

    p[0] = None

# The timestamp ALWAYS must be a number of exactly 10 digits
def p_timestamp(p):
    'timestamp : NUM10'
    p[0] = p[1]

# The Peer AS can come as a 10-digit number (e.g. 4294967295) or
# as a 9-digit number (the vast majority of real-world cases)
def p_peer_as_10(p):
    'peer_as : NUM10'
    p[0] = p[1]

def p_peer_as_9(p):
    'peer_as : NUM9'
    p[0] = p[1]

def p_prefix(p):
    'prefix : IPADDR SLASH mask'
    p[0] = None

# The mask always fits in 9 digits (ranges from 0 to 32)
def p_mask(p):
    'mask : NUM9'
    value = p[1]
    if not (0 <= value <= 32):
        print(
            f"Semantic error [Line {p.lineno(1)}]: "
            f"Mask out of range (0-32): {value}"
        )
        parser.has_errors = True
    p[0] = value

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
    p[0] = p[1]

# Same as peer_as: an AS within the AS_PATH can also have 10 or 9
# digits, for the same reason (ASN up to 32 bits)
def p_as_num_10(p):
    'as_num : NUM10'
    p[0] = p[1]

def p_as_num_9(p):
    'as_num : NUM9'
    p[0] = p[1]

def p_as_set(p):
    'as_set : LBRACE as_set_list RBRACE'
    p[0] = p[2]

def p_as_set_list_multiple(p):
    'as_set_list : as_num COMMA as_set_list'
    p[0] = [p[1]] + p[3]

def p_as_set_list_single(p):
    'as_set_list : as_num'
    p[0] = [p[1]]

def p_error(p):
    if p is not None:
        print(f"Syntax error [Line {p.lineno}]")
    else:
        print("Syntax error: unexpected end of input")

    parser.has_errors = True

parser = yacc.yacc()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python mrtparser.py <mrt_dump_file>")
        sys.exit(1)

    input_path = sys.argv[1]

    with open(input_path, 'r') as f:
        data = f.read()

    lexer.lineno = 1
    lexer.has_errors = False
    lexer.input(data)

    collected_tokens = []

    while True:
        tok = lexer.token()
        if not tok:
            break
        collected_tokens.append(tok)

    choice = input(
        "Show results in (C)onsole or save them in a (F)ile? [C/F]: "
    ).strip().upper()

    lexer.lineno = 1
    lexer.has_errors = False
    parser.has_errors = False

    parser.parse(data, lexer=lexer, tracking=True)
    if choice == 'F':
        with open("ParserOutput.txt", "w") as out_file:

            out_file.write("=== Tokens ===\n")

            for tok in collected_tokens:
                out_file.write(f"{tok}\n")

            if lexer.has_errors:
                out_file.write("MRT File with INCORRECT tokens\n")
            else:
                out_file.write("MRT File with CORRECT tokens :)\n")

            out_file.write("\n=== Parse ===\n")

            if lexer.has_errors or parser.has_errors:
                out_file.write("MRT File with INCORRECT syntax\n")
            else:
                out_file.write("MRT File with CORRECT syntax :)\n")

        print("Results saved in ParserOutput.txt")

    else:
        print("=== Tokens ===")

        for tok in collected_tokens:
            print(tok)

        if lexer.has_errors:
            print("MRT File with INCORRECT tokens")
        else:
            print("MRT File with CORRECT tokens :)")

        print("\n=== Parse ===")

        if lexer.has_errors or parser.has_errors:
            print("MRT File with INCORRECT syntax")
        else:
            print("MRT File with CORRECT syntax :)")
