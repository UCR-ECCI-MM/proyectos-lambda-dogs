"""Pruebas de las funcionalidades 1-3 (índices construidos en el parser)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import parser as P                                    # noqa: E402
from analysis import (filas_aristas, normalizar_prefijo,   # noqa: E402
                      routes_between_prefixes)

L = "TABLE_DUMP2|1785888000|B|{ip}|{peer}|{pref}|{path}\n"


def dump(*lineas):
    return "".join(L.format(ip=i, peer=p, pref=x, path=a)
                   for i, p, x, a in lineas)


BASE = dump(
    ("1.1.1.1", 3549, "8.8.8.0/24", "3549 174 15169"),
    ("2.2.2.2", 6939, "8.8.8.0/24", "6939 15169"),
    ("3.3.3.3", 7018, "8.8.8.0/24", "7018 3257 64512"),
    ("1.1.1.1", 3549, "9.9.9.0/24", "3549 3356 3356 100"),
)


class Consultas(unittest.TestCase):
    def setUp(self):
        self.res = P.parse_text(BASE)

    def test_conflicto_de_origen(self):
        self.assertTrue(self.res.ok)
        self.assertEqual(self.res.index.conflicts, {"8.8.8.0/24"})

    def test_mismo_origen_no_es_conflicto(self):
        res = P.parse_text(dump(
            ("1.1.1.1", 3549, "8.8.8.0/24", "3549 174 15169"),
            ("2.2.2.2", 6939, "8.8.8.0/24", "6939 15169")))
        self.assertEqual(res.index.conflicts, set())

    def test_aristas_de_un_as(self):
        filas = filas_aristas(self.res.index, 3549)
        self.assertEqual([(f[0], f[1]) for f in filas],
                         [("1.1.1.1", "8.8.8.0/24"), ("1.1.1.1", "9.9.9.0/24")])
        self.assertEqual(filas_aristas(self.res.index, 15169), [])

    def test_prepending_sin_autoarista(self):
        self.assertNotIn(3356, self.res.as_graph.adjacency[3356])

    def test_rutas_entre_prefijos(self):
        oa, ob, rutas, trunc = routes_between_prefixes(
            self.res, "9.9.9.0/24", "8.8.8.0/24")
        self.assertEqual(oa, [100])
        self.assertEqual(ob, [15169, 64512])
        self.assertEqual(rutas, [[100, 3356, 3549, 174, 15169]])
        self.assertFalse(trunc)

    def test_normalizar_prefijo(self):
        self.assertEqual(normalizar_prefijo(" 8.8.8.0/24 "), "8.8.8.0/24")
        self.assertIsNone(normalizar_prefijo("8.8.8/24"))
        self.assertIsNone(normalizar_prefijo("1.2.3.4/40"))


if __name__ == "__main__":
    unittest.main()
