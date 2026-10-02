"""
Colector de errores y advertencias del análisis del archivo MRT.

En vez de imprimir los problemas conforme aparecen, el lexer, el parser y
las acciones semánticas los agregan aquí. Así la aplicación (consola o UI)
decide cómo mostrarlos: tabla, panel, archivo, etc.
"""

from dataclasses import dataclass, field

LEXICO = 'léxico'
SINTACTICO = 'sintáctico'
SEMANTICO = 'semántico'
ARCHIVO = 'archivo'

ERROR = 'error'
ADVERTENCIA = 'advertencia'


@dataclass
class Problema:
    linea: int            # 0 si no aplica (p. ej. archivo inexistente)
    tipo: str             # LEXICO | SINTACTICO | SEMANTICO | ARCHIVO
    severidad: str        # ERROR | ADVERTENCIA
    campo: str            # nombre del campo (o '' si no aplica)
    lexema: str           # texto problemático (o '' si no aplica)
    mensaje: str

    def __str__(self):
        donde = f"línea {self.linea}" if self.linea else "archivo"
        campo = f", campo {self.campo}" if self.campo else ""
        lexema = f" ('{self.lexema}')" if self.lexema else ""
        return (f"[{self.severidad} {self.tipo}] {donde}{campo}: "
                f"{self.mensaje}{lexema}")


@dataclass
class Colector:
    problemas: list = field(default_factory=list)
    # Líneas que ya tienen un error léxico: el parser no repite el reporte
    lineas_con_error_lexico: set = field(default_factory=set)

    def agregar(self, linea, tipo, severidad, mensaje, campo='', lexema=''):
        self.problemas.append(
            Problema(linea, tipo, severidad, campo, str(lexema), mensaje))

    def error(self, linea, tipo, mensaje, campo='', lexema=''):
        self.agregar(linea, tipo, ERROR, mensaje, campo, lexema)

    def advertencia(self, linea, tipo, mensaje, campo='', lexema=''):
        self.agregar(linea, tipo, ADVERTENCIA, mensaje, campo, lexema)

    @property
    def errores(self):
        return [p for p in self.problemas if p.severidad == ERROR]

    @property
    def advertencias(self):
        return [p for p in self.problemas if p.severidad == ADVERTENCIA]

    def limpiar(self):
        self.problemas.clear()
        self.lineas_con_error_lexico.clear()
