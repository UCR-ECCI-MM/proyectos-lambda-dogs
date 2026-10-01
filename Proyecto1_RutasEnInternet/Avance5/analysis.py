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