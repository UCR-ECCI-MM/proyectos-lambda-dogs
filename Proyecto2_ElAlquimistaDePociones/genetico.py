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

def cruce(p1, p2, pc, rng):
    """Cruce de un punto con probabilidad pc. Devuelve dos hijos."""
    n = len(p1)
    if n > 1 and rng.random() < pc:
        corte = rng.randint(1, n - 1)
        return p1[:corte] + p2[corte:], p2[:corte] + p1[corte:]
    return p1[:], p2[:]


def mutacion(x, pm, rng, p_swap=0.1):
    """Inclusión/exclusión de cada gen con probabilidad pm; además, con
    probabilidad p_swap intercambia un ingrediente dentro por uno fuera."""
    for i in range(len(x)):
        if rng.random() < pm:
            x[i] ^= 1
    if rng.random() < p_swap:
        dentro = [i for i, v in enumerate(x) if v]
        fuera = [i for i, v in enumerate(x) if not v]
        if dentro and fuera:
            x[rng.choice(dentro)] = 0
            x[rng.choice(fuera)] = 1
    return x

def algoritmo_genetico(inst, params=None, semilla=None):
    """Devuelve (mejor_x, mejor_Z, segundos, historial).
    mejor_x es la mejor receta VÁLIDA encontrada (None si nunca hubo una).
    historial[g] = mejor Z válido hasta la generación g (None si aún no hay)."""
    params = params or ParametrosGA()
    rng = random.Random(semilla)
    pm = params.pm if params.pm is not None else 1.0 / inst.n
    inicio = time.perf_counter()

    pob = poblacion_inicial(inst, params.tam_poblacion, rng,
                            params.sembrar_heuristica)
    mejor_x, mejor_z = None, None
    historial = []
    sin_mejora = 0

    for gen in range(params.generaciones + 1):
        aptitudes = [aptitud(inst, x, params.penalizacion) for x in pob]

        mejoro = False
        for x in pob:
            if es_valida(inst, x):
                z = potencia(inst, x)
                if mejor_z is None or z > mejor_z:
                    mejor_x, mejor_z, mejoro = x[:], z, True
        historial.append(mejor_z)
        sin_mejora = 0 if mejoro else sin_mejora + 1

        if gen == params.generaciones or sin_mejora >= params.paciencia:
            break

        # Elitismo + reproducción
        orden = sorted(range(len(pob)), key=lambda i: aptitudes[i], reverse=True)
        nueva = [pob[i][:] for i in orden[:params.elitismo]]
        while len(nueva) < params.tam_poblacion:
            p1 = seleccion_torneo(pob, aptitudes, params.tam_torneo, rng)
            p2 = seleccion_torneo(pob, aptitudes, params.tam_torneo, rng)
            h1, h2 = cruce(p1, p2, params.pc, rng)
            nueva.append(mutacion(h1, pm, rng))
            if len(nueva) < params.tam_poblacion:
                nueva.append(mutacion(h2, pm, rng))
        pob = nueva

    return mejor_x, mejor_z, time.perf_counter() - inicio, historial

if __name__ == "__main__":
    from fuerza_bruta import fuerza_bruta
    inst = generar_instancia(16, semilla=42)
    _, z_opt, t_fb = fuerza_bruta(inst)
    print(f"Óptimo (fuerza bruta): Z={z_opt} ({t_fb:.2f} s)")
    for s in range(5):
        x, z, t, _ = algoritmo_genetico(inst, semilla=s)
        brecha = (z_opt - z) / z_opt * 100 if z is not None else float("nan")
        print(f"semilla {s}: Z={z} | brecha={brecha:.2f}% | {t:.2f} s")
