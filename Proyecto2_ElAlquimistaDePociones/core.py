import json
import random
from dataclasses import dataclass, asdict

PROPIEDADES = ("fuerza", "sigilo", "mana")

NOMBRES = ["Raíz de mandrágora", "Esencia de sombra", "Lágrimas de cristal",
           "Polvo de luna", "Ala de murciélago", "Musgo espectral",
           "Escama de dragón", "Savia de roble antiguo", "Ceniza de fénix",
           "Hongo brillante"]

@dataclass
class Ingrediente:
    nombre: str
    peso: int
    props: list  # [fuerza, sigilo, mana]


@dataclass
class Instancia:
    ingredientes: list   # lista de Ingrediente
    capacidad: int       # W
    umbrales: list       # T_k
    alfas: list          # alpha_k
    semilla: int = None

    @property
    def n(self):
        return len(self.ingredientes)

# ---------- Evaluación ----------

def peso_total(inst, x):
    return sum(ing.peso for ing, xi in zip(inst.ingredientes, x) if xi)


def props_totales(inst, x):
    tot = [0, 0, 0]
    for ing, xi in zip(inst.ingredientes, x):
        if xi:
            for k in range(3):
                tot[k] += ing.props[k]
    return tot


def potencia(inst, x):
    """Z(x) = sum_k alfa_k * sum_i a_ik * x_i"""
    tot = props_totales(inst, x)
    return sum(a * t for a, t in zip(inst.alfas, tot))


def es_valida(inst, x):
    if peso_total(inst, x) > inst.capacidad:
        return False
    tot = props_totales(inst, x)
    return all(t >= u for t, u in zip(tot, inst.umbrales))


def violacion(inst, x):
    """Cuánto se incumple (0 si es válida). Útil para la penalización del genético."""
    v = max(0, peso_total(inst, x) - inst.capacidad)
    tot = props_totales(inst, x)
    v += sum(max(0, u - t) for t, u in zip(tot, inst.umbrales))
    return v

# ---------- Generador de instancias ----------

def generar_instancia(n, semilla=42, frac_capacidad=0.4, frac_umbral=0.6,
                      alfas=(1.0, 1.0, 1.0)):
    """
    Instancia reproducible (misma semilla => mismos datos).
    Garantiza que exista al menos una solución válida.
    """
    rng = random.Random(semilla)
    ingredientes = []
    for i in range(n):
        nombre = f"{NOMBRES[i % len(NOMBRES)]} #{i + 1}"
        peso = rng.randint(1, 30)
        props = [rng.randint(1, 50) for _ in range(3)]
        ingredientes.append(Ingrediente(nombre, peso, props))

    capacidad = int(sum(ing.peso for ing in ingredientes) * frac_capacidad)

    # Receta de referencia aleatoria que cabe en el caldero
    orden = list(range(n))
    rng.shuffle(orden)
    ref, peso_ref = [0] * n, 0
    for i in orden:
        if peso_ref + ingredientes[i].peso <= capacidad:
            ref[i] = 1
            peso_ref += ingredientes[i].peso

    base = [sum(ingredientes[i].props[k] for i in range(n) if ref[i])
            for k in range(3)]
    umbrales = [int(b * frac_umbral) for b in base]

    return Instancia(ingredientes, capacidad, umbrales, list(alfas), semilla)


