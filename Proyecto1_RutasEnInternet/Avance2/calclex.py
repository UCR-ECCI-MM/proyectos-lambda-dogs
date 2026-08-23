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
 
# Recognizes the slash that separates the IP address from the mask length
def t_SLASH(t):
    r'/'
    t.lexer.after_slash = True
    return t


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

# Recognizes pipe separators and advances to the next field.
def t_PIPE(t):
    r'\|'
    t.lexer.field += 1
    t.lexer.after_slash = False
    return t

# A regular expression rule with some action code
def t_NUMBER(t):
    r'\d+'
    value = int(t.value)
    is_mask = t.lexer.field == 6 and getattr(t.lexer, 'after_slash', False)
    t.lexer.after_slash = False
    t.type = 'MASK' if is_mask else 'NUMBER'
    t.value = value
    return t
 
 # Define a rule so we can track line numbers
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.lexer.field = 0
    t.lexer.after_slash = False
 
# A string containing ignored characters (spaces and tabs)
t_ignore  = ' \t'
 
# Error handling rule
def t_error(t):
     print("Illegal character '%s'" % t.value[0])
     t.lexer.skip(1)
 
# Build the lexer
lexer = lex.lex()

# Test
data = 'TABLE_DUMP2|1421996402|B|012.802.62.15|1252|1.0.128.0/17|9002 4826 38803 56203'

lexer.field = 0
lexer.after_slash = False
lexer.has_errors = False

# Give the lexer some input
lexer.input(data)
 
# Tokenize
while True:
     tok = lexer.token()
     if not tok: 
         break      # No more input
     print(tok)
