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

class ASGraph:

    def __init__(self):
        self.adjacency = {}  # dict: AS number -> set of neighboring AS numbers

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


# Global containers populated dynamically while the file is parsed
records = []
routing_table = {}
all_as_numbers = set()
as_graph = ASGraph()


def flatten_as_path(as_path):
    flat = []
    for element in as_path:
        if isinstance(element, set):
            flat.extend(sorted(element))
        else:
            flat.append(element)
    return flat


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

    record_type = p[1]
    timestamp = p[3]
    state = p[5]
    peer_ip = p[7]
    peer_as = p[9]
    prefix = p[11]
    as_path = p[13]

    as_numbers = flatten_as_path(as_path)

    if peer_as not in as_numbers:
        print(
            f"Semantic error [Line {p.lineno(1)}]: "
            f"PEER_AS ({peer_as}) does not appear in AS_PATH {sorted(as_numbers)}"
        )
        parser.has_errors = True

    record = {
        'record_type': record_type,
        'timestamp': timestamp,
        'state': state,
        'peer_ip': peer_ip,
        'peer_as': peer_as,
        'prefix': prefix,
        'as_path': as_path,
    }
    # list
    records.append(record)

    prefix_key = f"{prefix['ip']}/{prefix['mask']}"
    # dict
    routing_table.setdefault(prefix_key, []).append(record)

    # set: every distinct AS number seen so far
    all_as_numbers.update(as_numbers)
    all_as_numbers.add(peer_as)

    # graph: AS-level adjacency implied by this AS_PATH
    for left, right in zip(as_numbers, as_numbers[1:]):
        as_graph.add_edge(left, right)
    if as_numbers:
        as_graph.add_node(as_numbers[0])

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

    # Reset the dynamic structures so re-runs in the same process start clean
    records.clear()
    routing_table.clear()
    all_as_numbers.clear()
    as_graph.adjacency.clear()

    parser.parse(data, lexer=lexer, tracking=True)

    structures_summary = (
        "\n=== Dynamically built structures ===\n"
        f"Records parsed (list):        {len(records)}\n"
        f"Distinct prefixes (dict):     {len(routing_table)}\n"
        f"Distinct AS numbers (set):    {len(all_as_numbers)}\n"
        f"AS graph nodes:               {len(as_graph.nodes())}\n"
        f"AS graph edges:               {len(as_graph.edges())}\n"
    )

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

            out_file.write(structures_summary)

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

        print(structures_summary)
