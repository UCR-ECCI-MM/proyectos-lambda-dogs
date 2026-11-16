# genetico.py
# Algoritmo genético para el Alquimista de Pociones
import random
import time
from dataclasses import dataclass

from core import generar_instancia, es_valida, potencia, violacion


@dataclass
class ParametrosGA:
    tam_poblacion: int = 100
    generaciones: int = 200
    pc: float = 0.9              # probabilidad de cruce
    pm: float = None             # probabilidad de mutación por gen (None => 1/N)
    tam_torneo: int = 3
    elitismo: int = 2            # mejores individuos que pasan intactos
    penalizacion: float = 10.0   # castigo por unidad de violación
    paciencia: int = 50          # generaciones sin mejora para parar
    sembrar_heuristica: bool = False


def aptitud(inst, x, penalizacion):
    """Z(x) si es válida; si no, Z(x) menos penalización proporcional a la violación."""
    return potencia(inst, x) - penalizacion * violacion(inst, x)
