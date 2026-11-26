# demo_vivo.py
# Para probar el genético con otros parámetros SIN tocar el resto del código.
from core import generar_instancia, es_valida
from heuristica import heuristica_reparacion
from genetico import algoritmo_genetico, ParametrosGA

# ================= PARÁMETROS =================
N = 40                 # tamaño de la instancia (ingredientes)
SEMILLA_INSTANCIA = 42
SEMILLAS_GA = range(5) # 5 corridas del genético

POBLACION = 100        # calibrado: 100 (probados: 20, 50, 100)
PC = 0.9               # probabilidad de cruce (probados: 0.7, 0.9)
PM_FACTOR = 1          # pm = PM_FACTOR / N (probados: 0.5, 1, 2)
TORNEO = 3             # tamaño de torneo (probados: 2, 3, 5)
ELITISMO = 2           # (probados: 0, 1, 2, 5)
PENALIZACION = 10      # (probados: 2, 5, 10, 20, 50)
GENERACIONES = 200     # no calibrado
PACIENCIA = 50         # no calibrado
SEMBRAR_HEURISTICA = False   # True = una receta inicial viene de la heurística
# ============================================================

inst = generar_instancia(N, SEMILLA_INSTANCIA, frac_umbral=1.0, alfas=(1.0, 0.2, 0.2))
params = ParametrosGA(tam_poblacion=POBLACION, pc=PC, pm=PM_FACTOR / N,
                      tam_torneo=TORNEO, elitismo=ELITISMO,
                      penalizacion=PENALIZACION, generaciones=GENERACIONES,
                      paciencia=PACIENCIA, sembrar_heuristica=SEMBRAR_HEURISTICA)

xh, zh, th = heuristica_reparacion(inst)
print(f"N={N} | heurística con reparación: Z={zh} | válida={es_valida(inst, xh)}")
print(f"Parámetros GA: {params}\n")
for s in SEMILLAS_GA:
    x, z, t, hist = algoritmo_genetico(inst, params, semilla=s)
    print(f"semilla {s}: Z={z} | generaciones={len(hist)-1} | {t:.2f} s")