# heuristica.py
# Heurística "Regla del Alquimista Experto" (versión simple y versión con reparación)
import time

from core import (generar_instancia, es_valida, potencia, props_totales,
                  peso_total)


def eficiencia(inst, i):
    """Eficiencia mágica: e_i = (sum_k alfa_k * a_ik) / w_i"""
    ing = inst.ingredientes[i]
    return sum(a * p for a, p in zip(inst.alfas, ing.props)) / ing.peso
