"""
Pruebas de la detección de errores del Avance 5.

Ejecutar desde la carpeta Avance5/:
    python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import parser as P  # noqa: E402
from errores import LEXICO, SINTACTICO, SEMANTICO, ARCHIVO  # noqa: E402

OK = "TABLE_DUMP2|1785888000|B|177.101.16.80|53046|7.0.0.0/8|53046 61626 749"


def linea(**cambios):
    """Línea válida con campos reemplazados (por nombre)."""
    campos = dict(rt="TABLE_DUMP2", ts="1785888000", st="B",
                  ip="177.101.16.80", pas="53046", pref="7.0.0.0/8",
                  path="53046 61626 749")
    campos.update(cambios)
    return "|".join(campos[k] for k in
                    ("rt", "ts", "st", "ip", "pas", "pref", "path"))


class Base(unittest.TestCase):
    def parse(self, texto):
        return P.parse_text(texto)

    def assertUnError(self, res, tipo, linea_esperada, texto_en_mensaje=None):
        errs = res.colector.errores
        self.assertEqual(len(errs), 1, [str(e) for e in errs])
        self.assertEqual(errs[0].tipo, tipo)
        self.assertEqual(errs[0].linea, linea_esperada)
        if texto_en_mensaje:
            self.assertIn(texto_en_mensaje, errs[0].mensaje)
        return errs[0]


class TestValidos(Base):
    def test_linea_valida(self):
        r = self.parse(OK + "\n")
        self.assertTrue(r.ok)
        self.assertEqual(len(r.records), 1)
        self.assertEqual(r.colector.problemas, [])

    def test_sin_salto_final(self):
        self.assertTrue(self.parse(OK).ok)

    def test_crlf_y_lineas_en_blanco(self):
        r = self.parse("\r\n\n" + OK + "\r\n\r\n\n" + OK + "\r\n")
        self.assertTrue(r.ok)
        self.assertEqual(len(r.records), 2)

    def test_as_set_y_peer_dentro_del_set(self):
        r = self.parse(linea(path="{53046,7} 3356 {1,2}"))
        self.assertTrue(r.ok, [str(e) for e in r.colector.errores])

    def test_estado_no_se_comparte_entre_ejecuciones(self):
        a = self.parse(OK)
        b = self.parse(OK + "\n" + OK)
        self.assertEqual(len(a.records), 1)
        self.assertEqual(len(b.records), 2)


class TestSemantica(Base):
    def test_peer_as_debe_ser_el_primero(self):
        r = self.parse(linea(path="61626 53046 749"))
        e = self.assertUnError(r, SEMANTICO, 1, "debe comenzar con el peer AS")
        self.assertIn("AS path", e.campo)
        self.assertEqual(len(r.records), 0)        # registro descartado

    def test_peer_as_solo_en_medio_no_basta(self):
        r = self.parse(linea(path="1 53046"))
        self.assertUnError(r, SEMANTICO, 1)

    def test_mascara_mayor_a_32_es_error(self):
        r = self.parse(linea(pref="7.0.0.0/33"))
        self.assertUnError(r, SEMANTICO, 1, "máscara fuera de rango")

    def test_mascara_0_y_32_son_advertencia_y_se_cargan(self):
        r = self.parse(linea(pref="0.0.0.0/0") + "\n" +
                       linea(pref="1.1.1.1/32"))
        self.assertTrue(r.ok)
        self.assertEqual(len(r.colector.advertencias), 2)
        self.assertEqual(len(r.records), 2)

    def test_mascara_1_y_31_sin_advertencia(self):
        r = self.parse(linea(pref="1.0.0.0/1") + "\n" +
                       linea(pref="1.1.1.0/31"))
        self.assertEqual(r.colector.problemas, [])

    def test_mascara_estricta(self):
        P.MASK_ESTRICTA = True
        try:
            r = self.parse(linea(pref="0.0.0.0/0"))
            self.assertUnError(r, SEMANTICO, 1)
        finally:
            P.MASK_ESTRICTA = False


class TestUnaLineaUnRegistro(Base):
    def test_registro_partido_en_dos_lineas(self):
        r = self.parse("TABLE_DUMP2|1785888000|B|177.101.16.80|\n"
                       "53046|7.0.0.0/8|53046\n")
        self.assertFalse(r.ok)
        self.assertEqual(len(r.records), 0)
        self.assertEqual(r.colector.errores[0].linea, 1)

    def test_dos_registros_en_una_linea(self):
        r = self.parse(OK + " " + OK + "\n")
        self.assertFalse(r.ok)
        self.assertEqual(r.colector.errores[0].tipo, SINTACTICO)

    def test_as_path_partido_en_dos_lineas(self):
        r = self.parse(linea(path="53046") + "\n61626\n")
        self.assertFalse(r.ok)


class TestSintaxis(Base):
    def test_linea_sin_as_path(self):
        r = self.parse(linea(path=""))
        e = self.assertUnError(r, SINTACTICO, 1, "fin de línea inesperado")
        self.assertIn("AS path", e.campo)

    def test_linea_con_pocos_campos(self):
        r = self.parse("TABLE_DUMP2|1785888000|B\n")
        e = self.assertUnError(r, SINTACTICO, 1, "solo tiene 3 de 7 campos")
        self.assertIn("state", e.campo)

    def test_campos_de_mas(self):
        r = self.parse(OK + "|749\n")
        self.assertTrue(any("más de 7 campos" in e.mensaje
                            for e in r.colector.errores))

    def test_as_set_mal_cerrado(self):
        r = self.parse(linea(path="53046 {123"))
        e = self.assertUnError(r, SINTACTICO, 1)
        self.assertIn("'}'", e.mensaje)

    def test_as_set_vacio(self):
        r = self.parse(linea(path="53046 {}"))
        self.assertFalse(r.ok)

    def test_timestamp_con_9_digitos(self):
        r = self.parse(linea(ts="178588800"))
        e = self.assertUnError(r, SINTACTICO, 1, "10 dígitos")
        self.assertIn("timestamp", e.campo)
        self.assertEqual(e.lexema, "178588800")


class TestLexico(Base):
    def test_octeto_mayor_a_255(self):
        r = self.parse(linea(ip="256.1.1.1"))
        e = self.assertUnError(r, LEXICO, 1, "dirección IP inválida")
        self.assertIn("peer IP", e.campo)
        self.assertEqual(e.lexema, "256.1.1.1")

    def test_ip_con_ceros_a_la_izquierda(self):
        self.assertUnError(self.parse(linea(ip="01.2.3.4")), LEXICO, 1)

    def test_ip_con_3_octetos(self):
        self.assertUnError(self.parse(linea(ip="1.2.3")), LEXICO, 1)

    def test_state_invalido(self):
        for malo in ("X", "b", "BB"):
            r = self.parse(linea(st=malo))
            e = self.assertUnError(r, LEXICO, 1)
            self.assertIn("state", e.campo)

    def test_record_type_invalido(self):
        r = self.parse(linea(rt="TABLE_DUMP3"))
        e = self.assertUnError(r, LEXICO, 1)
        self.assertIn("record type", e.campo)

    def test_ceros_a_la_izquierda_en_numero(self):
        r = self.parse(linea(pas="053046", path="053046"))
        self.assertEqual(len(r.colector.errores), 2)
        self.assertTrue(all("ceros" in e.mensaje for e in r.colector.errores))

    def test_numero_de_11_digitos_no_se_parte_en_dos(self):
        r = self.parse(linea(path="53046 12345678901"))
        e = self.assertUnError(r, LEXICO, 1, "11 dígitos")
        self.assertEqual(e.lexema, "12345678901")

    def test_timestamp_fuera_de_32_bits(self):
        r = self.parse(linea(ts="9999999999"))
        e = self.assertUnError(r, LEXICO, 1, "32 bits")
        self.assertIn("timestamp", e.campo)

    def test_peer_as_fuera_de_32_bits(self):
        r = self.parse(linea(pas="4294967296", path="4294967296"))
        self.assertEqual(len(r.colector.errores), 2)

    def test_peer_as_maximo_valido(self):
        r = self.parse(linea(pas="4294967295", path="4294967295"))
        self.assertTrue(r.ok)

    def test_un_error_lexico_no_duplica_error_sintactico(self):
        r = self.parse(linea(st="X"))
        self.assertEqual(len(r.colector.errores), 1)


class TestRecuperacion(Base):
    def test_reporta_todos_los_errores_y_sigue(self):
        texto = "\n".join([
            OK,
            linea(st="X"),                 # 2
            linea(pref="7.0.0.0/99"),      # 3
            "TABLE_DUMP2|1785888000|B",    # 4
            OK,
            "basura",                      # 6
            linea(path="1 2"),             # 7  (peer 53046 no es el primero)
            OK,
        ]) + "\n"
        r = self.parse(texto)
        lineas = sorted({e.linea for e in r.colector.errores})
        self.assertEqual(lineas, [2, 3, 4, 6, 7])
        self.assertEqual(len(r.records), 3)       # las 3 líneas buenas

    def test_lineas_malas_consecutivas(self):
        texto = "\n".join([linea(st="X")] * 5 + [OK]) + "\n"
        r = self.parse(texto)
        self.assertEqual([e.linea for e in r.colector.errores], [1, 2, 3, 4, 5])
        self.assertEqual(len(r.records), 1)

    def test_error_sintactico_consecutivo(self):
        texto = "a|b\nTABLE_DUMP2|1\nTABLE_DUMP2|2|\n" + OK + "\n"
        r = self.parse(texto)
        self.assertEqual(len({e.linea for e in r.colector.errores}), 3)
        self.assertEqual(len(r.records), 1)

    def test_numero_de_linea_correcto_con_lineas_en_blanco(self):
        r = self.parse("\n\n" + OK + "\n\n" + linea(st="X") + "\n")
        self.assertEqual(r.colector.errores[0].linea, 5)


class TestArchivo(Base):
    def test_archivo_vacio(self):
        for contenido in ("", "   \n\n \t\n"):
            r = self.parse(contenido)
            self.assertUnError(r, ARCHIVO, 0, "vacío")

    def test_archivo_inexistente(self):
        r = P.parse_file("/ruta/que/no/existe.txt")
        self.assertUnError(r, ARCHIVO, 0, "no existe")

    def test_ruta_es_carpeta(self):
        r = P.parse_file(tempfile.gettempdir())
        self.assertUnError(r, ARCHIVO, 0, "carpeta")

    def test_archivo_real(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False,
                                         encoding='utf-8') as f:
            f.write(OK + "\n")
            ruta = f.name
        try:
            self.assertTrue(P.parse_file(ruta).ok)
        finally:
            os.remove(ruta)

    def test_bytes_no_utf8(self):
        with tempfile.NamedTemporaryFile('wb', suffix='.txt',
                                         delete=False) as f:
            f.write(OK.encode() + b"\n" + OK.encode().replace(b"B|", b"\xff|")
                    + b"\n")
            ruta = f.name
        try:
            r = P.parse_file(ruta)
            self.assertFalse(r.ok)
            self.assertEqual(r.colector.errores[0].linea, 2)
        finally:
            os.remove(ruta)


if __name__ == '__main__':
    unittest.main()
