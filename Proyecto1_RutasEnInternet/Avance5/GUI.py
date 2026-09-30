"""
GUI Raylib para el analizador MRT.
"""

import sys
from dataclasses import dataclass, field

import pyray as rl

from parser import parse_file
from Analisis import fmt_path, ip_key, routes_between_prefixes
from display import strip_ansi, render_problemas

MAX_NODOS_RUTA = 12
MAX_RUTAS = 1000

FS = 18
ROW_H = 22

BG = rl.Color(30, 32, 38, 255)
PANEL = rl.Color(40, 43, 51, 255)
INPUT_BG = rl.Color(24, 26, 31, 255)
BTN = rl.Color(62, 92, 160, 255)
BTN_HOT = rl.Color(84, 118, 196, 255)
TAB_ON = rl.Color(62, 92, 160, 255)
TAB_OFF = rl.Color(50, 54, 64, 255)
TEXT = rl.Color(225, 228, 235, 255)
DIM = rl.Color(140, 146, 160, 255)
RED = rl.Color(240, 100, 100, 255)
GREEN = rl.Color(110, 220, 140, 255)
YELLOW = rl.Color(240, 200, 100, 255)
HEADER = rl.Color(150, 190, 255, 255)

TABS = ["Resumen", "Origen de prefijos", "Aristas de un AS", "Rutas A -> B"]
