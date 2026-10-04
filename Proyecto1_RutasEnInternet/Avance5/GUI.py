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

# Helpers de UI (modo inmediato)

def hover(r):
    return rl.check_collision_point_rec(rl.get_mouse_position(), r)


def clicked(r):
    return rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT) and hover(r)


def button(x, y, w, h, label):
    r = rl.Rectangle(x, y, w, h)
    rl.draw_rectangle_rec(r, BTN_HOT if hover(r) else BTN)
    tw = rl.measure_text(label, FS)
    rl.draw_text(label, int(x + (w - tw) / 2), int(y + (h - FS) / 2), FS, TEXT)
    return clicked(r)


class TextBox:
    def _init_(self, label, digits_only=False):
        self.label = label
        self.text = ""
        self.digits_only = digits_only
        self.rect = rl.Rectangle(0, 0, 0, 0)

    def type_chars(self):
        while True:
            c = rl.get_char_pressed()
            if c == 0:
                break
            ch = chr(c)
            if c >= 32 and (not self.digits_only or ch.isdigit()):
                self.text += ch
        if rl.is_key_pressed(rl.KEY_BACKSPACE) or \
                rl.is_key_pressed_repeat(rl.KEY_BACKSPACE):
            self.text = self.text[:-1]
        if (rl.is_key_down(rl.KEY_LEFT_CONTROL) or
                rl.is_key_down(rl.KEY_RIGHT_CONTROL)) and \
                rl.is_key_pressed(rl.KEY_V):
            clip = rl.get_clipboard_text() or ""
            clip = clip.strip().replace("\n", "")
            if self.digits_only:
                clip = "".join(ch for ch in clip if ch.isdigit())
            self.text += clip

    def draw(self, x, y, w, h, focused):
        self.rect = rl.Rectangle(x, y, w, h)
        rl.draw_rectangle_rec(self.rect, INPUT_BG)
        rl.draw_rectangle_lines(int(x), int(y), int(w), int(h),
                                HEADER if focused else DIM)
        shown = self.text
        while shown and rl.measure_text(shown, FS) > w - 16:
            shown = shown[1:] # muestra el final
        if shown:
            rl.draw_text(shown, int(x + 8), int(y + (h - FS) / 2), FS, TEXT)
        else:
            rl.draw_text(self.label, int(x + 8), int(y + (h - FS) / 2),
                         FS, DIM)
        if focused and int(rl.get_time() * 2) % 2 == 0:
            cx = int(x + 8 + rl.measure_text(shown, FS))
            rl.draw_rectangle(cx + 1, int(y + 6), 2, int(h - 12), TEXT)

@dataclass
class View:
    header: list = field(default_factory=list)
    cols: list = field(default_factory=lambda: [0])
    rows: list = field(default_factory=list)
    info: str = ""
    scroll: int = 0

# Aplicación

class App:
    def _init_(self):
        self.res = None
        self.tab = 0
        self.views = [View() for _ in TABS]
        self.path_box = TextBox("Ruta del archivo MRT (o arrastre uno aquí)")
        self.as_box = TextBox("Número de AS", digits_only=True)
        self.pa_box = TextBox("Prefijo A (ej. 8.8.8.0/24)")
        self.pb_box = TextBox("Prefijo B (ej. 1.1.1.0/24)")
        self.focus = self.path_box
        self.status = "Cargue un archivo MRT."
        self.pending = None
        self.views[0].rows = [(["Cargue un archivo MRT para comenzar."], DIM)]

    # -- carga -----------------------------------------------------------
    def request_load(self, path):
        self.path_box.text = path
        self.status = f"Analizando {path} ..."
        self.pending = path

    def do_load(self, path):
        res = parse_file(path)
        self.res = res
        self.views[1] = View()
        self.views[2] = View()
        self.views[3] = View()
        self.build_summary()
        if res.ok:
            self.build_conflicts()
            self.status = (f"OK: {len(res.records)} registros, "
                           f"{len(res.index.conflicts)} prefijo(s) con "
                           f"más de un origen.")
            self.tab = 1 if res.index.conflicts else 0
        else:
            self.status = (f"El archivo tiene {len(res.colector.errores)} "
                           f"error(es); corríjalos para usar los análisis.")
            self.tab = 0
# -- construcción de vistas ------------------------------------------
    def build_summary(self):
        res, v = self.res, self.views[0]
        rows = []
        col = res.colector
        if res.ok:
            rows.append((["Archivo analizado sin errores."], GREEN))
        else:
            rows.append((["Archivo con errores (no se habilitan los "
                          "análisis)."], RED))
        rows.append(([f"Líneas: {res.total_lines}    "
                      f"Registros válidos: {len(res.records)}    "
                      f"Errores: {len(col.errores)}"], TEXT))
        if res.ok:
            rows.append(([f"Prefijos distintos: {len(res.routing_table)}    "
                          f"AS distintos: {len(res.all_as_numbers)}    "
                          f"Aristas AS-AS: {len(res.as_graph.edges())}"],
                         TEXT))
        rows.append(([""], TEXT))
        for ln in render_problemas(col):
            s = strip_ansi(ln)
            rows.append(([s], YELLOW if s.lstrip().startswith("!") else RED))
        v.rows, v.scroll = rows, 0

    def build_conflicts(self):
        idx, v = self.res.index, self.views[1]
        v.header = ["Prefijo", "AS origen", "Rutas", "Líneas",
                    "Ejemplo de AS path"]
        v.cols = [0, 170, 280, 350, 520]
        v.rows = []
        for prefix, por_origen in idx.conflict_rows():
            first = True
            for origen in sorted(por_origen):
                regs = por_origen[origen]
                lineas = ",".join(str(l) for l, _ in regs[:4])
                if len(regs) > 4:
                    lineas += ",..."
                v.rows.append(([prefix if first else "", f"AS{origen}",
                                str(len(regs)), lineas,
                                fmt_path(regs[0][1])],
                               RED if first else YELLOW))
                first = False
        n = len(idx.conflicts)
        v.info = (f"{n} prefijo(s) reportado(s) con más de un AS origen "
                  f"(posible prefix hijacking)." if n else
                  "Ningún prefijo tiene orígenes distintos.")
        v.scroll = 0
        