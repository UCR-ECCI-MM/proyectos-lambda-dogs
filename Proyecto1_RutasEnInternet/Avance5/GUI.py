"""
GUI Raylib para el analizador MRT.
"""

import sys
from dataclasses import dataclass, field

import pyray as rl

from parser import parse_file
from analysis import fmt_path, ip_key, routes_between_prefixes
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
    def __init__(self, label, digits_only=False):
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
            shown = shown[1:]
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

class App:
    def __init__(self):
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

    def query_edges(self):
        v = self.views[2]
        v.header = ["IP del peer (arista)", "Prefijo", "AS path"]
        v.cols = [0, 210, 400]
        v.rows, v.scroll = [], 0
        txt = self.as_box.text.strip()
        if not txt:
            v.info = "Escriba un número de AS."
            return
        asn = int(txt)
        data = self.res.index.edges_of(asn)
        if not data:
            if asn in self.res.all_as_numbers:
                v.info = (f"AS{asn} aparece en AS paths pero nunca como "
                          f"peer: no tiene IPs de arista en el archivo.")
            else:
                v.info = f"AS{asn} no aparece en el archivo."
            return
        total = 0
        for ip in sorted(data, key=ip_key):
            first = True
            for prefix, path, _line in sorted(data[ip],
                                              key=lambda t: (t[0], t[2])):
                v.rows.append(([ip if first else "", prefix, fmt_path(path)],
                               HEADER if first else TEXT))
                first = False
                total += 1
        v.info = (f"AS{asn}: {len(data)} arista(s), {total} prefijo(s) "
                  f"conocido(s) a través de ellas.")

    def query_routes(self):
        v = self.views[3]
        v.header = ["#", "AS", "Ruta"]
        v.cols = [0, 70, 130]
        v.rows, v.scroll = [], 0
        a, b = self.pa_box.text.strip(), self.pb_box.text.strip()
        if not a or not b:
            v.info = "Escriba los dos prefijos (formato del campo 6)."
            return
        oa, ob, rutas, trunc = routes_between_prefixes(
            self.res, a, b, MAX_NODOS_RUTA, MAX_RUTAS)
        if not oa or not ob:
            falta = a if not oa else b
            v.info = f"El prefijo {falta} no existe en el archivo."
            return
        for i, r in enumerate(rutas, 1):
            v.rows.append(([str(i), str(len(r)),
                            " -> ".join(f"AS{n}" for n in r)], TEXT))
        o_a = ",".join(f"AS{x}" for x in oa)
        o_b = ",".join(f"AS{x}" for x in ob)
        v.info = (f"{a} (origen {o_a})  ->  {b} (origen {o_b}): "
                  f"{len(rutas)} ruta(s)"
                  + (f" [límite de {MAX_RUTAS} alcanzado]" if trunc else "")
                  + f"; máx. {MAX_NODOS_RUTA} AS por ruta."
                  if rutas else
                  f"No hay ruta entre {a} y {b} (máx. {MAX_NODOS_RUTA} "
                  f"AS por ruta).")

    def submit(self):
        if self.focus is self.path_box:
            if self.path_box.text.strip():
                self.request_load(self.path_box.text.strip())
        elif self.res and self.res.ok:
            if self.tab == 2:
                self.query_edges()
            elif self.tab == 3:
                self.query_routes()

    # -- frame -------------------------------------------------------------
    def current_boxes(self):
        if self.tab == 2:
            return [self.as_box]
        if self.tab == 3:
            return [self.pa_box, self.pb_box]
        return []

    def frame(self):
        W, H = rl.get_screen_width(), rl.get_screen_height()

        # teclado
        self.focus.type_chars()
        if rl.is_key_pressed(rl.KEY_ENTER) or \
                rl.is_key_pressed(rl.KEY_KP_ENTER):
            self.submit()
        if rl.is_key_pressed(rl.KEY_TAB):
            boxes = [self.path_box] + self.current_boxes()
            i = boxes.index(self.focus) if self.focus in boxes else -1
            self.focus = boxes[(i + 1) % len(boxes)]

        view = self.views[self.tab]
        area_top = 140 if self.tab in (2, 3) else 96
        visible = max(1, (H - area_top - 30 - ROW_H) // ROW_H)
        wheel = rl.get_mouse_wheel_move()
        if wheel:
            view.scroll -= int(wheel * 3)
        if rl.is_key_pressed(rl.KEY_PAGE_DOWN):
            view.scroll += visible
        if rl.is_key_pressed(rl.KEY_PAGE_UP):
            view.scroll -= visible
        if rl.is_key_pressed(rl.KEY_HOME):
            view.scroll = 0
        if rl.is_key_pressed(rl.KEY_END):
            view.scroll = len(view.rows)
        view.scroll = max(0, min(view.scroll, max(0, len(view.rows) - visible)))

        rl.begin_drawing()
        rl.clear_background(BG)

        # barra de archivo
        self.path_box.draw(10, 10, W - 130, 30, self.focus is self.path_box)
        if clicked(self.path_box.rect):
            self.focus = self.path_box
        if button(W - 110, 10, 100, 30, "Cargar"):
            self.focus = self.path_box
            self.submit()

        # pestañas
        tx = 10
        for i, name in enumerate(TABS):
            w = rl.measure_text(name, FS) + 24
            r = rl.Rectangle(tx, 50, w, 30)
            rl.draw_rectangle_rec(r, TAB_ON if i == self.tab else TAB_OFF)
            rl.draw_text(name, int(tx + 12), 56, FS, TEXT)
            if clicked(r):
                self.tab = i
                self.focus = (self.current_boxes() or [self.path_box])[0] \
                    if i in (2, 3) else self.focus
            tx += w + 4

        # consultas
        usable = self.res is not None and self.res.ok
        if self.tab in (2, 3):
            if self.tab == 2:
                self.as_box.draw(10, 90, 220, 30, self.focus is self.as_box)
                bx = 240
            else:
                half = (W - 140) // 2
                self.pa_box.draw(10, 90, half - 10, 30,
                                 self.focus is self.pa_box)
                self.pb_box.draw(half + 5, 90, half - 10, 30,
                                 self.focus is self.pb_box)
                bx = W - 125
            for bxo in self.current_boxes():
                if clicked(bxo.rect):
                    self.focus = bxo
            if button(bx, 90, 110, 30, "Buscar") and usable:
                self.submit()
            if not usable:
                rl.draw_text("Los análisis requieren un archivo sin errores.",
                             10, 124, FS - 2, YELLOW)

        # tabla / lista
        top = area_top
        if view.info and self.tab != 0:
            rl.draw_text(view.info, 10, top - 4 if self.tab in (2, 3) else
                         top - 12, FS - 2, HEADER)
        top += 22 if self.tab != 0 else 0
        rl.draw_rectangle(0, top, W, H - top - 28, PANEL)
        y = top + 4
        if view.header:
            for x, h in zip(view.cols, view.header):
                rl.draw_text(h, 10 + x, y, FS, HEADER)
            y += ROW_H
            rl.draw_line(0, y - 2, W, y - 2, DIM)
        rl.begin_scissor_mode(0, y, W, H - y - 28)
        for i in range(view.scroll, min(len(view.rows), view.scroll + visible
                                        + 1)):
            cells, color = view.rows[i]
            for x, c in zip(view.cols, cells):
                if c:
                    rl.draw_text(c, 10 + x, y, FS, color)
            y += ROW_H
        rl.end_scissor_mode()
        if not view.rows and self.tab != 0:
            rl.draw_text("Sin resultados todavía.", 10, top + 30, FS, DIM)

        # barra de estado
        rl.draw_rectangle(0, H - 28, W, 28, TAB_OFF)
        rl.draw_text(self.status, 10, H - 24, FS - 2, TEXT)
        if len(view.rows) > visible:
            pos = f"{view.scroll + 1}-{min(len(view.rows), view.scroll + visible)}/{len(view.rows)}"
            rl.draw_text(pos, W - rl.measure_text(pos, FS - 2) - 10, H - 24,
                         FS - 2, DIM)
        rl.end_drawing()

        if self.pending:
            p, self.pending = self.pending, None
            self.do_load(p)

def main():
    rl.set_config_flags(rl.FLAG_WINDOW_RESIZABLE)
    rl.init_window(1150, 700, "Analizador MRT")
    rl.set_window_min_size(800, 500)
    rl.set_exit_key(rl.KEY_NULL)
    rl.set_target_fps(60)
    app = App()
    if len(sys.argv) > 1:
        app.request_load(sys.argv[1])
    while not rl.window_should_close():
        app.frame()
    rl.close_window()


if __name__ == "__main__":
    main()