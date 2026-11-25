# fuerza_bruta.py
import time
from core import generar_instancia, es_valida, potencia


def fuerzabruta(inst):
    """Devuelve (mejor_x, mejor_Z, segundos). Si no hay solución válida: (None, None, t)."""
    n = inst.n
    mejor_x, mejor_z = None, None
    inicio = time.perf_counter()

    for mascara in range(1 << n):
        x = [(mascara >> i) & 1 for i in range(n)]
        if es_valida(inst, x):
            z = potencia(inst, x)
            if mejor_z is None or z > mejor_z:
                mejor_x, mejor_z = x, z

    return mejor_x, mejor_z, time.perf_counter() - inicio


if __name__ == "__main__":
    # Tiempo vs. N (se detiene si una corrida pasa de 60 s)
    for n in range(8, 26):
        inst = generar_instancia(n, semilla=42)
        x, z, t = fuerza_bruta(inst)
        print(f"N={n:2d} | Z={z} | {t:.3f} s")
        if t > 60:
            print("Límite práctico alcanzado")
            break
