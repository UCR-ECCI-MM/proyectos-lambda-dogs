# ------------------------------------------------------------
 # calclex.py
 #
 # tokenizer for a simple expression evaluator for
 # numbers and +,-,*,/
 # ------------------------------------------------------------
import ply.lex as lex
import re
 
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
)

# Regular expression rules for simple tokens
# Made this this way to have an easy way to change the regexes if needed
RECORD_TYPE_RE = re.compile(r'^TABLE_DUMP2$')
STATE_RE = re.compile(r'^[BAW]$')
UINT32_RE = re.compile(
    r'^(0|[1-9]\d{0,8}|[1-3]\d{9}|4('
    r'[01]\d{8}|2[0-8]\d{7}|29[0-3]\d{6}|294[0-8]\d{5}|2949[0-5]\d{4}|'
    r'29496[0-6]\d{3}|294967[01]\d{2}|2949672[0-8]\d|29496729[0-5]))$'
)
OCTET_RE = r'(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)'
MASK_RE = r'(3[0-2]|[12]?\d)'
IPADDR_RE = re.compile(
    r'' +
    OCTET_RE + r'\.' +
    OCTET_RE + r'\.' +
    OCTET_RE + r'\.' +
    OCTET_RE +
    r'(/' + MASK_RE + r')?'
)

def is_valid_record_type(text):
    return bool(RECORD_TYPE_RE.match(text))


def is_valid_state(text):
    return bool(STATE_RE.match(text))


def is_valid_timestamp(text):
    return bool(UINT32_RE.match(text))


def is_valid_peer_as(text):
    return bool(UINT32_RE.match(text))


def is_valid_mask(text):
    return bool(MASK_RE.match(text))


def is_valid_as_path_num(text):
    return bool(UINT32_RE.match(text))


def is_valid_ipaddr(text):
    return bool(IPADDR_RE.match(text))


def t_INITIAL_RECORD_TYPE(t):
    r'[A-Za-z_][A-Za-z0-9_]*'
    if not is_valid_record_type(t.value):
        print("Invalid record type '%s'" % t.value)
        t.lexer.has_errors = True
        return None
    return t


def t_STATE(t):
    r'[A-Za-z]+'
    if not is_valid_state(t.value):
        print("Invalid state '%s'" % t.value)
        t.lexer.has_errors = True
        return None
    return t


def t_IPADDR(t):
    r'\d+\.\d+\.\d+\.\d+'
    if not is_valid_ipaddr(t.value):
        print("Invalid IP address '%s'" % t.value)
        t.lexer.has_errors = True
        return None
    return t


def t_SLASH(t):
    r'/'
    t.lexer.begin('mask')
    return t


def t_TIMESTAMP(t):
    r'\d+'
    if not is_valid_timestamp(t.value):
        print("Invalid timestamp '%s'" % t.value)
        t.lexer.has_errors = True
        return None
    t.value = int(t.value)
    return t


def t_PEER_AS(t):
    r'\d+'
    if not is_valid_peer_as(t.value):
        print("Invalid peer AS '%s'" % t.value)
        t.lexer.has_errors = True
        return None
    t.value = int(t.value)
    return t


def t_MASK(t):
    r'\d+'
    if not is_valid_mask(t.value):
        print("Invalid mask length '%s'" % t.value)
        t.lexer.has_errors = True
        return None
    t.value = int(t.value)
    return t


def t_AS_PATH_NUM(t):
    r'\d+'
    if not is_valid_as_path_num(t.value):
        print("Invalid AS number in path '%s'" % t.value)
        t.lexer.has_errors = True
        return None
    t.value = int(t.value)
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.lexer.begin('INITIAL')


t_ignore = ' \t'


def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.has_errors = True
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
