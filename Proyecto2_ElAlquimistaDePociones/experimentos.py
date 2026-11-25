# experimentos.py
# Corridas, tablas (CSV) y gráficos para el análisis.
# Uso: python3 experimentos.py {tiempo|comparacion|escalabilidad|convergencia|todo}
import argparse
import csv
import os
from statistics import mean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from core import generar_instancia, es_valida
from fuerzabruta import fuerzabruta
from heuristica import heuristica_simple, heuristica_reparacion
from genetico import algoritmo_genetico, ParametrosGA

DIR = "resultados"
INST_KW = dict(frac_umbral=1.0, alfas=(1.0, 0.2, 0.2))  # instancias exigentes
PARAMS_GA = ParametrosGA()   # reemplazar por los valores calibrados (calibracion_ga.py)


def guardar_csv(nombre, filas):
    os.makedirs(DIR, exist_ok=True)
    ruta = os.path.join(DIR, nombre)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print(f"Guardado {ruta}")


def guardar_fig(nombre):
    os.makedirs(DIR, exist_ok=True)
    ruta = os.path.join(DIR, nombre)
    plt.tight_layout()
    plt.savefig(ruta, dpi=150)
    plt.close()
    print(f"Guardado {ruta}")


# ---------- 1. Tiempo de la fuerza bruta vs N ----------

def exp_tiempo(n_min=8, n_max=22, limite=60):
    filas = []
    for n in range(n_min, n_max + 1):
        inst = generar_instancia(n, 42, **INST_KW)
        _, z, t = fuerzabruta(inst)
        filas.append({"n": n, "z_optimo": z, "tiempo_s": round(t, 4)})
        print(f"N={n:2d} | Z={z} | {t:.3f} s")
        if t > limite:
            print("Límite práctico alcanzado")
            break
    guardar_csv("tiempo_fb.csv", filas)
    plt.figure(figsize=(6, 4))
    plt.semilogy([f["n"] for f in filas], [f["tiempo_s"] for f in filas], "o-")
    plt.xlabel("N (ingredientes)")
    plt.ylabel("Tiempo (s, escala log)")
    plt.title("Fuerza bruta: tiempo vs. N")
    plt.grid(True, which="both", alpha=0.3)
    guardar_fig("tiempo_fb.png")


# ---------- 2. Comparación de las tres técnicas (N pequeños, con óptimo) ----------

def exp_comparacion(ns=(10, 12, 14, 16, 18), sem_inst=(1, 2, 3, 4, 5), sem_ga=range(5)):
    filas = []
    for n in ns:
        for si in sem_inst:
            inst = generar_instancia(n, si, **INST_KW)
            _, z_opt, t_fb = fuerzabruta(inst)
            filas.append(dict(tecnica="fuerza_bruta", n=n, sem_inst=si, sem_ga="",
                              z=z_opt, brecha=0.0, valida=True, tiempo_s=t_fb))
            for nombre, f in (("heuristica_simple", heuristica_simple),
                              ("heuristica_reparacion", heuristica_reparacion)):
                x, z, t = f(inst)
                v = es_valida(inst, x)
                filas.append(dict(tecnica=nombre, n=n, sem_inst=si, sem_ga="", z=z,
                                  brecha=(z_opt - z) / z_opt * 100 if v else "",
                                  valida=v, tiempo_s=t))
            for sg in sem_ga:
                _, z, t, _ = algoritmo_genetico(inst, PARAMS_GA, semilla=sg)
                filas.append(dict(tecnica="genetico", n=n, sem_inst=si, sem_ga=sg, z=z,
                                  brecha=(z_opt - z) / z_opt * 100 if z is not None else "",
                                  valida=z is not None, tiempo_s=t))
            print(f"N={n}, instancia {si} lista")
    guardar_csv("comparacion_detalle.csv", filas)

    tecnicas = ["fuerza_bruta", "heuristica_simple", "heuristica_reparacion", "genetico"]
    resumen = []
    for tec in tecnicas:
        for n in ns:
            fs = [f for f in filas if f["tecnica"] == tec and f["n"] == n]
            br = [f["brecha"] for f in fs if f["brecha"] != ""]
            resumen.append(dict(
                tecnica=tec, n=n,
                brecha_media=round(mean(br), 3) if br else "",
                pct_validas=round(100 * sum(f["valida"] for f in fs) / len(fs), 1),
                tiempo_medio_s=round(mean(f["tiempo_s"] for f in fs), 5)))
    guardar_csv("comparacion_resumen.csv", resumen)
    for r in resumen:
        print(r)

    fig, ejes = plt.subplots(1, 3, figsize=(15, 4))
    for tec in tecnicas:
        rs = [r for r in resumen if r["tecnica"] == tec]
        xs = [r["n"] for r in rs]
        ejes[0].plot(xs, [r["brecha_media"] if r["brecha_media"] != "" else float("nan")
                          for r in rs], "o-", label=tec)
        ejes[1].plot(xs, [r["pct_validas"] for r in rs], "o-", label=tec)
        ejes[2].semilogy(xs, [r["tiempo_medio_s"] for r in rs], "o-", label=tec)
    ejes[0].set_title("Brecha media vs. óptimo (%)")
    ejes[1].set_title("% de recetas válidas")
    ejes[2].set_title("Tiempo medio (s, log)")
    for e in ejes:
        e.set_xlabel("N")
        e.grid(True, alpha=0.3)
    ejes[0].legend()
    guardar_fig("comparacion.png")


# ---------- 3. Escalabilidad (N grandes, sin fuerza bruta) ----------

def exp_escalabilidad(ns=(20, 50, 100, 200, 400), sem_ga=range(3)):
    filas = []
    for n in ns:
        inst = generar_instancia(n, 42, **INST_KW)
        for nombre, f in (("heuristica_simple", heuristica_simple),
                          ("heuristica_reparacion", heuristica_reparacion)):
            x, z, t = f(inst)
            filas.append(dict(tecnica=nombre, n=n, sem_ga="", z=z,
                              valida=es_valida(inst, x), tiempo_s=t))
        for sg in sem_ga:
            _, z, t, _ = algoritmo_genetico(inst, PARAMS_GA, semilla=sg)
            filas.append(dict(tecnica="genetico", n=n, sem_ga=sg, z=z,
                              valida=z is not None, tiempo_s=t))
        print(f"N={n} listo")
    guardar_csv("escalabilidad.csv", filas)

    fig, ejes = plt.subplots(1, 2, figsize=(11, 4))
    for tec in ("heuristica_simple", "heuristica_reparacion", "genetico"):
        xs, zs, ts = [], [], []
        for n in ns:
            fs = [f for f in filas if f["tecnica"] == tec and f["n"] == n]
            zv = [f["z"] for f in fs if f["valida"]]
            xs.append(n)
            zs.append(mean(zv) if zv else float("nan"))
            ts.append(mean(f["tiempo_s"] for f in fs))
        ejes[0].plot(xs, zs, "o-", label=tec)
        ejes[1].semilogy(xs, ts, "o-", label=tec)
    ejes[0].set_title("Z medio (solo recetas válidas)")
    ejes[1].set_title("Tiempo medio (s, log)")
    for e in ejes:
        e.set_xlabel("N")
        e.grid(True, alpha=0.3)
    ejes[0].legend()
    guardar_fig("escalabilidad.png")


# ---------- 4. Convergencia del genético ----------

def exp_convergencia(n=40, semillas=range(5)):
    inst = generar_instancia(n, 42, **INST_KW)
    _, z_h, _ = heuristica_reparacion(inst)
    plt.figure(figsize=(7, 4))
    for s in semillas:
        _, _, _, hist = algoritmo_genetico(inst, PARAMS_GA, semilla=s)
        plt.plot([h if h is not None else float("nan") for h in hist],
                 label=f"semilla {s}")
    plt.axhline(z_h, color="k", linestyle="--", label="heurística con reparación")
    plt.xlabel("Generación")
    plt.ylabel("Mejor Z válido")
    plt.title(f"Convergencia del algoritmo genético (N={n})")
    plt.legend()
    plt.grid(True, alpha=0.3)
    guardar_fig("convergencia.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("exp", choices=["tiempo", "comparacion", "escalabilidad",
                                    "convergencia", "todo"])
    a = ap.parse_args()
    if a.exp in ("tiempo", "todo"):
        exp_tiempo()
    if a.exp in ("comparacion", "todo"):
        exp_comparacion()
    if a.exp in ("escalabilidad", "todo"):
        exp_escalabilidad()
    if a.exp in ("convergencia", "todo"):
        exp_convergencia()
