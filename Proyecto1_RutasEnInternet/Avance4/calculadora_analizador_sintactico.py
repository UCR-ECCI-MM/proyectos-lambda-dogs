import sys
from lexer import tokens, lexer

# Temporary: used to test this part of the parser separately.
start = 'linea_inicio'

def p_linea_inicio(p):
    'linea_inicio : RECORD_TYPE PIPE TIMESTAMP PIPE STATE PIPE IPADDR'
    pass

# Fields 5 and 6
def p_prefijo(p):
    'prefijo : IPADDR SLASH NUMBER'
    mascara = p[3]
    if not (1 <= mascara <= 31):
        print(
            f"Syntax error [Line {p.lineno(1)}]: "
            f"prefix length out of range (1-31): {mascara}"
        )

def p_linea_parcial(p):
    'linea_parcial : linea_inicio PIPE NUMBER PIPE prefijo'
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
            s = input('mrt-p2 > ')
        except EOFError:
            break
        if not s:
            continue
        parser.parse(s, lexer=lexer)