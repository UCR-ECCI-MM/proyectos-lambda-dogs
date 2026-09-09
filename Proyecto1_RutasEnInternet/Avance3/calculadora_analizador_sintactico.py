# -----------------------------------------------------------------------------
# calc.py
#
# A simple calculator with variables -- all in one file.
# -----------------------------------------------------------------------------

# The lexer and token list are defined in lexer.py.
# We just import them here instead of defining them again.
import sys
from lexer import tokens, lexer

# Temporary: used to test this part of the parser separately.
start = 'linea_inicio'

def p_linea_inicio(p):
    'linea_inicio : RECORD_TYPE PIPE TIMESTAMP PIPE STATE PIPE IPADDR'
    pass

def p_error(p):
    if p:
        print(f"Syntax error [Line {p.lineno}]: unexpected token '{p.value}'")
    else:
        print("Syntax error: unexpected end of input")

import ply.yacc as yacc
parser = yacc.yacc()

if __name__ == '__main__':
    while True:
        try:
            s = input('mrt-p1 > ')
        except EOFError:
            break
        if not s:
            continue
        parser.parse(s, lexer=lexer)
