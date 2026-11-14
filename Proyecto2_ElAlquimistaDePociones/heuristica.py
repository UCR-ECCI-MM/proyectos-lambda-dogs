# heuristica.py
# Heurística "Regla del Alquimista Experto" (versión simple y versión con reparación)
import time

from core import (generar_instancia, es_valida, potencia, props_totales,
                  peso_total)


def eficiencia(inst, i):
    """Eficiencia mágica: e_i = (sum_k alfa_k * a_ik) / w_i"""
    ing = inst.ingredientes[i]
    return sum(a * p for a, p in zip(inst.alfas, ing.props)) / ing.peso

def heuristica_simple(inst):
    """Voraz por eficiencia mágica (no garantiza cumplir umbrales).
    Devuelve (x, Z, segundos)."""
    inicio = time.perf_counter()
    n = inst.n
    orden = sorted(range(n), key=lambda i: eficiencia(inst, i), reverse=True)
    x = [0] * n
    restante = inst.capacidad
    for i in orden:
        w = inst.ingredientes[i].peso
        if w <= restante:
            x[i] = 1
            restante -= w
    return x, potencia(inst, x), time.perf_counter() - inicio
