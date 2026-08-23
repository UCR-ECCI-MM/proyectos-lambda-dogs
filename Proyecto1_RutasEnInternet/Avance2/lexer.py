import sys
import time
import re
import ply.lex as lex


# List of all token types that can be recognized by the lexer
tokens = (
    'RECORD_TYPE',
    'STATE',
    'IPADDR',
    'PIPE',
    'SLASH',
    'NUMBER',
    'LBRACE',
    'RBRACE',
    'COMMA',
)


# Token rules and their corresponding regular expressions

# Recognizes the TABLE_DUMP2 value used at the beginning of each record
def t_RECORD_TYPE(t):
    r'TABLE_DUMP2\b'
    return t


# Recognizes the possible states of a record: B, A or W
def t_STATE(t):
    r'[BAW]\b'
    return t


# Recognizes IPv4 addresses and makes sure each octet is between 0 and 255
OCTET = r'(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)'

@lex.TOKEN(r'\b(' + OCTET + r'\.){3}' + OCTET + r'\b')
def t_IPADDR(t):
    return t


# Separators used between fields and between an address and its mask
t_PIPE = r'\|'
t_SLASH = r'/'


# Braces and commas used when an AS path contains a group of AS numbers
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_COMMA = r','


# Numbers used for timestamps, AS numbers, masks and AS paths
MAX_UINT32 = 2**32 - 1  # Maximum value for a 32-bit unsigned integer

def t_NUMBER(t):
    r'\d{1,10}'

    value = int(t.value)

    # Check that the number fits in the allowed 32-bit range
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


# Build the lexer using the rules defined above
lexer = lex.lex()


# Main program
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python mrtlex.py <mrt_dump_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    with open(input_path, 'r') as f:
        data = f.read()

    lexer.input(data)

    while True:
        tok = lexer.token()
        if not tok:
            break
        print(tok)

    if lexer.has_errors:
        print("archivo MRT con tokens incorrectos")
    else:
        print("archivo MRT con tokens correctos")