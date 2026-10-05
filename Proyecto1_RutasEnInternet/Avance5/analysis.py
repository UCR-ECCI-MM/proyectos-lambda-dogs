"""
Índices construidos DURANTE el parseo (desde las acciones de la gramática)
y consultas post-parseo del Avance 6.

Idea de diseño: cada registro válido se indexa una sola vez, en O(largo del
AS path), dentro de p_linea. Después ninguna consulta recorre la lista de
registros:

  * origins    : prefijo -> {AS origen -> [(línea, as_path)]}
                 + `conflicts`, el conjunto de prefijos con >1 origen,
                 que se actualiza en el mismo momento en que aparece el 2do
                 origen. Reportar anomalías es leer ese set.
  * by_peer    : AS peer -> {IP del peer -> [(prefijo, as_path, línea)]}
                 Consulta 2 = dos lookups en dict.
  * as_graph   : (ya existente) adyacencia. Consulta 3 = prefijo -> orígenes
                 (dict) y DFS sobre el grafo entre esos orígenes.
"""


from collections import defaultdict, deque


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def fmt_path(as_path):
    """[3549, {1,2}, 15169] -> '3549 {1,2} 15169'"""
    return ' '.join(
        '{' + ','.join(str(n) for n in sorted(e)) + '}'
        if isinstance(e, set) else str(e)
        for e in as_path)


def origins_of(as_path):
    """El origen de una ruta es su ÚLTIMO elemento (si es un AS_SET, todos
    sus miembros se consideran orígenes)."""
    last = as_path[-1]
    return sorted(last) if isinstance(last, set) else [last]


def ip_key(ip):
    try:
        return tuple(int(x) for x in ip.split('.'))
    except ValueError:
        return (999, 999, 999, 999)


# ---------------------------------------------------------------------------
# Índices
# ---------------------------------------------------------------------------

class Indices:
    def __init__(self):
        self.origins = defaultdict(lambda: defaultdict(list))
        self.conflicts = set()
        self.by_peer = defaultdict(lambda: defaultdict(list))

    # Se llama una vez por registro válido, desde p_linea.
    def add(self, prefix_txt, peer_as, peer_ip, as_path, line):
        por_origen = self.origins[prefix_txt]
        for o in origins_of(as_path):
            por_origen[o].append((line, as_path))
        if len(por_origen) > 1:
            self.conflicts.add(prefix_txt)
        self.by_peer[peer_as][peer_ip].append((prefix_txt, as_path, line))

    # -- Consulta 1 --------------------------------------------------------
    def conflict_rows(self):
        """[(prefijo, {origen: [(línea, path)]})] ordenado por prefijo."""
        return [(p, dict(self.origins[p])) for p in sorted(self.conflicts)]

    # -- Consulta 2 --------------------------------------------------------
    def edges_of(self, asn):
        """{ip: [(prefijo, as_path, línea)]} o None si el AS no es peer."""
        return self.by_peer.get(asn)

    # -- Consulta 3 (parte 1) ----------------------------------------------
    def origins_for(self, prefix_txt):
        d = self.origins.get(prefix_txt)
        return sorted(d) if d else []


# ---------------------------------------------------------------------------
# Consulta 3: todas las rutas simples entre dos AS en el grafo
# ---------------------------------------------------------------------------

def _distancias_desde(adj, dst):
    dist = {dst: 0}
    q = deque([dst])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def all_simple_paths(adj, src, dst, max_nodes=12, limit=1000):
    """Todas las rutas SIN repetir AS de src a dst (no solo la más corta).

    * DFS iterativo (sin recursión, no revienta el límite de Python).
    * Poda con distancias BFS desde dst: no se entra a ramas que ya no
      pueden llegar a dst dentro de `max_nodes`.
    * `limit` corta la enumeración (el número de rutas puede ser
      exponencial). Devuelve (rutas, truncado).
    """
    if src not in adj or dst not in adj:
        return [], False
    if src == dst:
        return [[src]], False
    dist = _distancias_desde(adj, dst)
    if src not in dist or dist[src] + 1 > max_nodes:
        return [], False

    paths = []
    path = [src]
    on_path = {src}
    stack = [iter(sorted(adj[src]))]
    while stack:
        nxt = next(stack[-1], None)
        if nxt is None:
            stack.pop()
            on_path.discard(path.pop())
            continue
        if nxt in on_path or nxt not in dist:
            continue
        if len(path) + 1 + dist[nxt] > max_nodes:
            continue                      # no alcanza a llegar a tiempo
        if nxt == dst:
            paths.append(path + [dst])
            if len(paths) >= limit:
                return paths, True
            continue
        path.append(nxt)
        on_path.add(nxt)
        stack.append(iter(sorted(adj[nxt])))
    return paths, False

def routes_between_prefixes(res, prefix_a, prefix_b, max_nodes=12,
                            limit=1000):
    """Rutas entre el/los AS que originan A y el/los que originan B.

    Devuelve (origenes_a, origenes_b, rutas, truncado).
    """
    oa = res.index.origins_for(prefix_a)
    ob = res.index.origins_for(prefix_b)
    adj = res.as_graph.adjacency
    rutas, truncado = [], False
    for a in oa:
        for b in ob:
            restante = limit - len(rutas)
            if restante <= 0:
                return oa, ob, rutas, True
            r, t = all_simple_paths(adj, a, b, max_nodes, restante)
            rutas.extend(r)
            truncado = truncado or t
    rutas.sort(key=lambda p: (len(p), p))
    return oa, ob, rutas, truncado


# ---------------------------------------------------------------------------
# Ayudas para la entrada del usuario y el formato (las usan la consola y la GUI)
# ---------------------------------------------------------------------------

import re

_PREFIJO_RE = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})$')


def normalizar_prefijo(txt):
    """'8.8.8.0/24' (campo 6) -> prefijo canónico, o None si no tiene esa forma."""
    m = _PREFIJO_RE.match((txt or '').strip())
    if not m:
        return None
    *octetos, mask = (int(g) for g in m.groups())
    if any(o > 255 for o in octetos) or mask > 32:
        return None
    return '.'.join(str(o) for o in octetos) + f'/{mask}'


def fmt_ruta(ruta):
    """[7018, 3257, 64512] -> '7018 -> 3257 -> 64512'"""
    return ' -> '.join(str(n) for n in ruta)


def filas_aristas(index, asn):
    """Consulta 2 lista para mostrar: [(ip, prefijo, 'as path', línea)] con las
    IP en orden numérico y los prefijos en orden. [] si el AS no es peer."""
    aristas = index.edges_of(asn)
    if not aristas:
        return []
    filas = []
    for ip in sorted(aristas, key=ip_key):
        for prefijo, path, linea in sorted(
                aristas[ip], key=lambda t: (ip_key(t[0].split('/')[0]),
                                            int(t[0].split('/')[1]), t[2])):
            filas.append((ip, prefijo, fmt_path(path), linea))
    return filas

def neighborhood(adj, root, depth=2, max_nodes=60):
    """Nodes within `depth` hops of root (BFS), capped at max_nodes."""
    if root not in adj:
        return set(), []
    seen = {root}
    frontier = [root]
    for _ in range(depth):
        nxt = []
        for u in frontier:
            for v in sorted(adj[u]):
                if v not in seen and len(seen) < max_nodes:
                    seen.add(v)
                    nxt.append(v)
        frontier = nxt
    edges = [(a, b) for a in seen for b in adj[a] if b in seen and a < b]
    return seen, edges


def force_layout(nodes, edges, iterations=150):
    """Fruchterman-Reingold layout. Returns {node: (x, y)} in [0, 1]."""
    import math
    import random
    rnd = random.Random(1)
    ns = sorted(nodes)
    pos = {n: [rnd.random(), rnd.random()] for n in ns}
    k = math.sqrt(1.0 / max(1, len(ns)))
    temp = 0.1
    for _ in range(iterations):
        disp = {n: [0.0, 0.0] for n in ns}
        for i, a in enumerate(ns):
            for b in ns[i + 1:]:
                dx = pos[a][0] - pos[b][0]
                dy = pos[a][1] - pos[b][1]
                d = max(math.hypot(dx, dy), 1e-4)
                f = k * k / d
                disp[a][0] += dx / d * f
                disp[a][1] += dy / d * f
                disp[b][0] -= dx / d * f
                disp[b][1] -= dy / d * f
        for a, b in edges:
            dx = pos[a][0] - pos[b][0]
            dy = pos[a][1] - pos[b][1]
            d = max(math.hypot(dx, dy), 1e-4)
            f = d * d / k
            disp[a][0] -= dx / d * f
            disp[a][1] -= dy / d * f
            disp[b][0] += dx / d * f
            disp[b][1] += dy / d * f
        for n in ns:
            dx, dy = disp[n]
            d = max(math.hypot(dx, dy), 1e-4)
            step = min(d, temp)
            pos[n][0] += dx / d * step
            pos[n][1] += dy / d * step
        temp *= 0.97
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    sx = (max(xs) - min(xs)) or 1.0
    sy = (max(ys) - min(ys)) or 1.0
    return {n: ((p[0] - min(xs)) / sx, (p[1] - min(ys)) / sy)
            for n, p in pos.items()}