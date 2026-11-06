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