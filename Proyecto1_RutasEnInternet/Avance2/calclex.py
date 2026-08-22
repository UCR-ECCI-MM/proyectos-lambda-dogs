# ------------------------------------------------------------
 # calclex.py
 #
 # tokenizer for a simple expression evaluator for
 # numbers and +,-,*,/
 # ------------------------------------------------------------
import ply.lex as lex
 
# List of token names.   This is always required
tokens = (
    'RECORD_TYPE',
    'PIPE',
    'STATE',
    'IPADDR',
    'SLASH',
    'TIMESTAMP',
    'PEER_AS',
    'MASK',
    'AS_PATH_NUM',
    'NUMBER',
)
 
# Regular expression rules for simple tokens
t_PLUS    = r'\+'
t_MINUS   = r'-'
t_TIMES   = r'\*'
t_DIVIDE  = r'/'
t_LPAREN  = r'\('
t_RPAREN  = r'\)'


# Identifies WORD tokens and validates them according to their field in the record.
def t_WORD(t):
    r'[A-Za-z_][A-Za-z0-9_]*'
    if t.lexer.field == 0:
        t.lexer.field = 1
        if t.value != 'TABLE_DUMP2':
            print("Invalid record type '%s'" % t.value)
            t.lexer.has_errors = True
            return None
        t.type = 'RECORD_TYPE'
        return t

    if t.lexer.field == 3:
        if t.value not in ('B', 'A', 'W'):
            print("Invalid state '%s'" % t.value)
            t.lexer.has_errors = True
            return None
        t.type = 'STATE'
        return t

    print("Unexpected word '%s'" % t.value)
    t.lexer.has_errors = True
    return None


# A regular expression rule with some action code
def t_NUMBER(t):
     r'\d+'
     t.value = int(t.value)    
     return t
 
 # Define a rule so we can track line numbers
def t_newline(t):
     r'\n+'
     t.lexer.lineno += len(t.value)
 
# A string containing ignored characters (spaces and tabs)
t_ignore  = ' \t'
 
# Error handling rule
def t_error(t):
     print("Illegal character '%s'" % t.value[0])
     t.lexer.skip(1)
 
# Build the lexer
lexer = lex.lex()

# Test it out
data = '''
3 + 4 * 10
  + -20 *2
'''
 
# Give the lexer some input
lexer.input(data)
 
# Tokenize
while True:
     tok = lexer.token()
     if not tok: 
         break      # No more input
     print(tok)