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
