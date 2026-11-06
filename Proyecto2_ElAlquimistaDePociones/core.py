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