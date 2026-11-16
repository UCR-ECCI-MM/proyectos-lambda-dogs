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

def poblacion_inicial(inst, tam, rng, sembrar=False):
    """Recetas aleatorias. Cada ingrediente entra con probabilidad W / (suma de pesos),
    para que las recetas iniciales ronden la capacidad del caldero."""
    total = sum(ing.peso for ing in inst.ingredientes)
    p = min(1.0, inst.capacidad / total)
    pob = [[1 if rng.random() < p else 0 for _ in range(inst.n)]
           for _ in range(tam)]
    if sembrar:
        from heuristica import heuristica_reparacion  # depende del módulo de la heurística
        pob[0] = heuristica_reparacion(inst)[0]
    return pob


def seleccion_torneo(pob, aptitudes, k, rng):
    """Toma k individuos al azar y devuelve una copia del de mayor aptitud."""
    candidatos = rng.sample(range(len(pob)), min(k, len(pob)))
    mejor = max(candidatos, key=lambda i: aptitudes[i])
    return pob[mejor][:]
