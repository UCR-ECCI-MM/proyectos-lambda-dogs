"""
Terminal display for the MRT/BGP parser — pure Python, no external
dependencies (no rich, no colorama). Box-drawing tables, ANSI colors and a
small AS-graph tree, built from the dynamic structures populated while
parsing (records / routing_table / all_as_numbers / as_graph).

Kept in its own file so parser.py stays focused on the lexer/grammar; this
module only knows about plain data (lists, dicts, sets) passed in by the
caller, so it doesn't need to import anything from parser.py.
"""

import re


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"


_ANSI_RE = re.compile(r'\033\[[0-9;]*m')


def strip_ansi(text):
    """Remove ANSI color codes — used when saving the report to a file."""
    return _ANSI_RE.sub('', text)


def _vlen(text):
    """Visible length of a string, ignoring ANSI color codes."""
    return len(strip_ansi(str(text)))


def _pad(cell, width):
    cell = str(cell)
    return cell + ' ' * (width - _vlen(cell))


def draw_table(headers, rows, title=None, title_color=C.CYAN):
    """Render a single-line box-drawing table as a list of text lines."""
    widths = [_vlen(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], _vlen(cell))

    top = '┌' + '┬'.join('─' * (w + 2) for w in widths) + '┐'
    sep = '├' + '┼'.join('─' * (w + 2) for w in widths) + '┤'
    bot = '└' + '┴'.join('─' * (w + 2) for w in widths) + '┘'
    head = '│ ' + ' │ '.join(
        f"{C.BOLD}{_pad(h, widths[i])}{C.RESET}" for i, h in enumerate(headers)
    ) + ' │'

    lines = []
    if title:
        lines.append(f"{title_color}{C.BOLD}{title}{C.RESET}")
    lines += [top, head, sep]
    lines += [
        '│ ' + ' │ '.join(_pad(cell, widths[i]) for i, cell in enumerate(row)) + ' │'
        for row in rows
    ]
    lines.append(bot)
    return lines


def draw_panel(title, kv_pairs, color=C.CYAN):
    """Render a double-line box with aligned 'label  value' rows."""
    key_w = max(_vlen(k) for k, _ in kv_pairs)
    val_w = max(_vlen(v) for _, v in kv_pairs)
    row_w = key_w + 2 + val_w
    inner_w = max(_vlen(title), row_w)

    top = '╔' + '═' * (inner_w + 2) + '╗'
    mid = '╠' + '═' * (inner_w + 2) + '╣'
    bot = '╚' + '═' * (inner_w + 2) + '╝'

    lines = [
        f"{color}{top}",
        f"║ {C.BOLD}{_pad(title, inner_w)}{C.RESET}{color} ║",
        mid,
    ]
    for k, v in kv_pairs:
        row = _pad(k, key_w) + '  ' + v.rjust(val_w)
        lines.append(f"║ {_pad(row, inner_w)} {color}║")
    lines.append(bot + C.RESET)
    return lines


def origin_as_of(record, flatten_as_path):
    """The origin AS of a route is the last hop of its AS_PATH (see
    project statement: 'Todo path comienza con el AS propio')."""
    return flatten_as_path(record['as_path'])[-1]


def find_conflicting_prefixes(routing_table, flatten_as_path):
    """Prefixes announced with more than one distinct origin AS — the
    'more than two/one ASes claiming the same prefix' anomaly (possible
    prefix hijacking) described in the project statement."""
    conflicts = []
    for prefix, recs in routing_table.items():
        origins = sorted({origin_as_of(r, flatten_as_path) for r in recs})
        if len(origins) > 1:
            conflicts.append((prefix, origins, len(recs)))
    conflicts.sort(key=lambda item: -len(item[1]))
    return conflicts


def render_structures_report(
    records,
    routing_table,
    all_as_numbers,
    as_graph,
    flatten_as_path,
    top_n=12,
    conflict_n=10,
    tree_children=5,
):
    """Build the whole terminal report (list of text lines) from the four
    dynamic structures populated by the parser's grammar actions."""
    out = []

    out += draw_panel(
        "RESUMEN DEL ARCHIVO",
        [
            ("Registros parseados (list)", f"{len(records):,}"),
            ("Prefijos distintos (dict)", f"{len(routing_table):,}"),
            ("AS distintos (set)", f"{len(all_as_numbers):,}"),
            ("Nodos del grafo de AS", f"{len(as_graph.nodes()):,}"),
            ("Aristas del grafo de AS", f"{len(as_graph.edges()):,}"),
        ],
    )

    if not records:
        out.append(f"\n{C.DIM}(Archivo sin registros que mostrar){C.RESET}")
        return out

    # --- Top AS by degree (how "central" it is in the topology) ---------
    origin_counts = {}
    for prefix, recs in routing_table.items():
        for o in {origin_as_of(r, flatten_as_path) for r in recs}:
            origin_counts[o] = origin_counts.get(o, 0) + 1

    ranked_as = sorted(all_as_numbers, key=lambda a: (-as_graph.degree(a), a))
    top_rows = [
        [as_num, as_graph.degree(as_num), origin_counts.get(as_num, 0)]
        for as_num in ranked_as[:top_n]
    ]
    out.append("")
    out += draw_table(
        ["AS", "Vecinos (grado)", "Prefijos originados"],
        top_rows,
        title=f"TOP {min(top_n, len(ranked_as))} AS MÁS CONECTADOS",
    )
    if len(ranked_as) > top_n:
        out.append(f"{C.DIM}… y {len(ranked_as) - top_n} AS más en el grafo{C.RESET}")

    # --- Prefixes with more than one origin AS (possible hijacking) -----
    conflicts = find_conflicting_prefixes(routing_table, flatten_as_path)
    out.append("")
    if conflicts:
        rows = [
            [
                prefix,
                f"{C.RED}{', '.join(str(o) for o in origins)}{C.RESET}",
                n_records,
            ]
            for prefix, origins, n_records in conflicts[:conflict_n]
        ]
        out += draw_table(
            ["Prefijo", "AS de origen en conflicto", "# Registros"],
            rows,
            title=f"⚠ POSIBLES PREFIX HIJACKS ({len(conflicts)} prefijo(s) en conflicto)",
            title_color=C.YELLOW,
        )
        if len(conflicts) > conflict_n:
            out.append(f"{C.DIM}… y {len(conflicts) - conflict_n} prefijo(s) más en conflicto{C.RESET}")
    else:
        out.append(f"{C.GREEN}✓ No se detectaron prefijos con más de un AS de origen{C.RESET}")

    # --- A small tree view of the AS graph, rooted at the most-connected
    #     AS, so the topology built from the file is actually visible ----
    root = ranked_as[0]
    out.append("")
    out.append(f"{C.CYAN}{C.BOLD}VISTA DEL GRAFO DE AS (raíz: el más conectado){C.RESET}")
    out.append(f"{C.MAGENTA}{C.BOLD}AS {root}{C.RESET} {C.DIM}(grado {as_graph.degree(root)}){C.RESET}")

    visited = {root}

    def walk(node, prefix, depth, max_depth):
        if depth > max_depth:
            return
        neighbors = sorted(as_graph.adjacency.get(node, set()) - visited)
        shown, hidden = neighbors[:tree_children], len(neighbors) - min(len(neighbors), tree_children)
        for i, nb in enumerate(shown):
            visited.add(nb)
            last = (i == len(shown) - 1) and hidden == 0
            connector = '└── ' if last else '├── '
            branch = '    ' if last else '│   '
            out.append(f"{prefix}{connector}AS {nb} {C.DIM}(grado {as_graph.degree(nb)}){C.RESET}")
            walk(nb, prefix + branch, depth + 1, max_depth)
        if hidden > 0:
            out.append(f"{prefix}└── {C.DIM}… y {hidden} AS más{C.RESET}")

    walk(root, '', 1, max_depth=2)

    return out


def _recortar(texto, n):
    texto = str(texto)
    return texto if len(texto) <= n else texto[:n - 1] + '…'


def render_problemas(colector, max_errores=30, max_advertencias=10):
    """Tablas de errores y advertencias encontrados al analizar el archivo
    (lista de líneas de texto). Recibe un errores.Colector."""
    out = []
    errores = colector.errores
    advertencias = colector.advertencias

    if errores:
        rows = [
            [e.linea or '-', e.tipo, e.campo or '-',
             _recortar(e.lexema, 28) or '-', e.mensaje]
            for e in errores[:max_errores]
        ]
        out += draw_table(
            ["Línea", "Tipo", "Campo", "Lexema", "Detalle"],
            rows,
            title=f"✗ ERRORES ({len(errores):,})",
            title_color=C.RED,
        )
        if len(errores) > max_errores:
            out.append(f"{C.DIM}… y {len(errores) - max_errores:,} "
                       f"error(es) más{C.RESET}")

    if advertencias:
        if out:
            out.append("")
        rows = [
            [a.linea or '-', _recortar(a.lexema, 28) or '-', a.mensaje]
            for a in advertencias[:max_advertencias]
        ]
        out += draw_table(
            ["Línea", "Lexema", "Detalle"],
            rows,
            title=f"⚠ ADVERTENCIAS ({len(advertencias):,})",
            title_color=C.YELLOW,
        )
        if len(advertencias) > max_advertencias:
            out.append(f"{C.DIM}… y {len(advertencias) - max_advertencias:,}"
                       f" advertencia(s) más{C.RESET}")

    if not errores and not advertencias:
        out.append(f"{C.GREEN}✓ Sin errores ni advertencias{C.RESET}")
    return out
