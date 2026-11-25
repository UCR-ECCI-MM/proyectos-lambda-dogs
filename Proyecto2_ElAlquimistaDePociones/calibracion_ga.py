# calibracion_ga.py
# Calibración de parámetros del algoritmo genético.
# Fase 1: rejilla de población x pc x pm x torneo.
# Fase 2: con la mejor configuración, se varían penalización y elitismo.
# Uso: python3 calibracion_ga.py
import csv
import itertools
import os
from dataclasses import replace
from statistics import mean

from core import generar_instancia
from fuerzabruta import fuerzabruta
from genetico import algoritmo_genetico, ParametrosGA

N = 22
SEMILLA_INSTANCIA = 3
INST_KW = dict(frac_umbral=1.0, alfas=(1.0, 0.2, 0.2))  # instancia exigente
SEMILLAS_GA = range(5)

POBLACIONES = [20, 50, 100]
PCS = [0.7, 0.9]
PM_FACTORES = [0.5, 1, 2]        # pm = factor / N
TORNEOS = [2, 3, 5]
PENALIZACIONES = [2, 5, 10, 20, 50]
ELITISMOS = [0, 1, 2, 5]

DIR = "resultados"


def evaluar(inst, z_ref, params):
    """Corre el GA con varias semillas. Una corrida sin receta válida cuenta como brecha 100%."""
    brechas, tiempos, validas = [], [], 0
    for s in SEMILLAS_GA:
        _, z, t, _ = algoritmo_genetico(inst, params, semilla=s)
        tiempos.append(t)
        if z is None:
            brechas.append(100.0)
        else:
            validas += 1
            brechas.append((z_ref - z) / z_ref * 100)
    return {"brecha_media": round(mean(brechas), 3),
            "brecha_peor": round(max(brechas), 3),
            "validas": validas,
            "tiempo_medio": round(mean(tiempos), 3)}


def guardar(nombre, filas):
    os.makedirs(DIR, exist_ok=True)
    ruta = os.path.join(DIR, nombre)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print(f"Guardado {ruta}")


def mostrar_top(filas, claves, k=5):
    filas = sorted(filas, key=lambda r: (r["brecha_media"], r["tiempo_medio"]))
    for r in filas[:k]:
        cfg = ", ".join(f"{c}={r[c]}" for c in claves)
        print(f"  {cfg} -> brecha={r['brecha_media']}% "
              f"(peor {r['brecha_peor']}%), válidas={r['validas']}/{len(SEMILLAS_GA)}, "
              f"{r['tiempo_medio']} s")
    return filas[0]


if __name__ == "__main__":
    inst = generar_instancia(N, SEMILLA_INSTANCIA, **INST_KW)
    _, z_ref, t_fb = fuerzabruta(inst)
    print(f"Instancia N={N}, óptimo (FB) Z={z_ref} ({t_fb:.1f} s)")

    # ---- Fase 1 ----
    filas1 = []
    combos = list(itertools.product(POBLACIONES, PCS, PM_FACTORES, TORNEOS))
    for i, (pob, pc, f, tor) in enumerate(combos, 1):
        params = ParametrosGA(tam_poblacion=pob, pc=pc, pm=f / N, tam_torneo=tor)
        fila = {"poblacion": pob, "pc": pc, "pm_factor": f, "torneo": tor}
        fila.update(evaluar(inst, z_ref, params))
        filas1.append(fila)
        print(f"[{i}/{len(combos)}] {fila}")
    guardar("calibracion_ga_fase1.csv", filas1)
    print("\nTop 5 de la fase 1:")
    mejor = mostrar_top(filas1, ["poblacion", "pc", "pm_factor", "torneo"])

    base = ParametrosGA(tam_poblacion=mejor["poblacion"], pc=mejor["pc"],
                        pm=mejor["pm_factor"] / N, tam_torneo=mejor["torneo"])

    # ---- Fase 2 ----
    filas2 = []
    for pen in PENALIZACIONES:
        fila = {"parametro": "penalizacion", "valor": pen}
        fila.update(evaluar(inst, z_ref, replace(base, penalizacion=pen)))
        filas2.append(fila)
    for el in ELITISMOS:
        fila = {"parametro": "elitismo", "valor": el}
        fila.update(evaluar(inst, z_ref, replace(base, elitismo=el)))
        filas2.append(fila)
    guardar("calibracion_ga_fase2.csv", filas2)
    print("\nFase 2 (penalización y elitismo sobre la mejor configuración):")
    for r in filas2:
        print(f"  {r['parametro']}={r['valor']} -> brecha={r['brecha_media']}%, "
              f"válidas={r['validas']}/{len(SEMILLAS_GA)}, {r['tiempo_medio']} s")
