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

def _violacion_de(inst, peso, tot):
    """Violación calculada a partir del peso y las propiedades ya acumuladas."""
    v = max(0, peso - inst.capacidad)
    return v + sum(max(0, u - t) for t, u in zip(tot, inst.umbrales))


def reparar(inst, x, max_iter=None):
    """Paso de reparación: en cada iteración aplica el movimiento (agregar un
    ingrediente o intercambiar uno dentro por uno fuera) que más reduce el
    incumplimiento de umbrales sin pasarse del peso. Para cuando la receta es
    válida o ningún movimiento mejora."""
    x = x[:]
    n = inst.n
    max_iter = max_iter or n
    peso = peso_total(inst, x)
    tot = props_totales(inst, x)

    for _ in range(max_iter):
        v_act = _violacion_de(inst, peso, tot)
        if v_act == 0:
            break
        dentro = [k for k in range(n) if x[k]]
        fuera = [k for k in range(n) if not x[k]]
        mejor, mejor_clave = None, None
        for j in fuera:
            ing_j = inst.ingredientes[j]
            for i in [None] + dentro:
                p = peso + ing_j.peso
                t = [tot[k] + ing_j.props[k] for k in range(3)]
                if i is not None:
                    ing_i = inst.ingredientes[i]
                    p -= ing_i.peso
                    t = [t[k] - ing_i.props[k] for k in range(3)]
                if p > inst.capacidad:
                    continue
                v = _violacion_de(inst, p, t)
                if v >= v_act:
                    continue
                z = sum(a * tk for a, tk in zip(inst.alfas, t))
                clave = (v, -z)  # menor violación; a igualdad, mayor Z
                if mejor_clave is None or clave < mejor_clave:
                    mejor_clave, mejor = clave, (i, j, p, t)
        if mejor is None:
            break
        i, j, peso, tot = mejor
        x[j] = 1
        if i is not None:
            x[i] = 0
    return x


def heuristica_reparacion(inst):
    """Heurística simple + reparación. Devuelve (x, Z, segundos)."""
    inicio = time.perf_counter()
    x, _, _ = heuristica_simple(inst)
    x = reparar(inst, x)
    return x, potencia(inst, x), time.perf_counter() - inicio

if __name__ == "__main__":
    for n in (10, 15, 20, 50):
        inst = generar_instancia(n, semilla=42)
        print(f"--- N={n} | W={inst.capacidad} | umbrales={inst.umbrales}")
        if n <= 16:
            from fuerza_bruta import fuerza_bruta
            print(f"{'óptimo (FB)':15s} Z={fuerza_bruta(inst)[1]}")
        for nombre, f in (("simple", heuristica_simple),
                          ("con reparación", heuristica_reparacion)):
            x, z, t = f(inst)
            print(f"{nombre:15s} Z={z:8.1f} | válida={es_valida(inst, x)} "
                  f"| {t * 1000:.2f} ms")
