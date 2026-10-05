"""
Raylib GUI for the MRT analyzer.

    pip install raylib
    python GUI.py [file.txt]

Tabs: Summary | Prefix origins (func. 1) | Edges of an AS (func. 2)
      | Routes A -> B (func. 3) | Graph
A file can be dropped onto the window, or its path typed followed by Enter.
"""

import sys
from dataclasses import dataclass, field

import pyray as rl

from parser import parse_file
from analysis import (fmt_path, fmt_ruta, filas_aristas, normalizar_prefijo,
                      routes_between_prefixes, neighborhood, force_layout)

MAX_ROUTE_NODES = 12
MAX_ROUTES = 1000
MAX_PROBLEMS = 300

FS = 18
ROW_H = 22
PAD = 20

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

TABS = ["Resumen", "Origen de prefijos", "Aristas de un AS", "Rutas A -> B", "Grafo"]
TAB_SUMMARY, TAB_CONFLICTS, TAB_EDGES, TAB_ROUTES, TAB_GRAPH = range(5)


def safe(s):
    """The default raylib font only draws Latin-1: anything else -> ASCII."""
    replacements = {'→': '->', '✗': 'x', '✓': 'v', '⚠': '!', '…': '...'}
    return ''.join(replacements.get(ch, ch if ord(ch) < 256 else '?')
                   for ch in s)

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


def clip_text(text, width):
    """Cut the text (adding '...') so it fits in `width` pixels."""
    if rl.measure_text(text, FS) <= width:
        return text
    while text and rl.measure_text(text + "...", FS) > width:
        text = text[:-1]
    return text + "..."


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
                rl.is_key_down(rl.KEY_RIGHT_CONTROL) or
                rl.is_key_down(rl.KEY_LEFT_SUPER)) and \
                rl.is_key_pressed(rl.KEY_V):
            clip = rl.get_clipboard_text() or ""
            if isinstance(clip, bytes):
                clip = clip.decode("utf-8", "replace")
            clip = clip.strip().replace("\n", "")
            if self.digits_only:
                clip = "".join(ch for ch in clip if ch.isdigit())
            self.text += clip

    def draw(self, x, y, w, h, focused):
        self.rect = rl.Rectangle(x, y, w, h)
        rl.draw_rectangle_rec(self.rect, INPUT_BG)
        rl.draw_rectangle_lines(int(x), int(y), int(w), int(h),
                                HEADER if focused else DIM)
        shown = safe(self.text)
        while shown and rl.measure_text(shown, FS) > w - 16:
            shown = shown[1:]  # show the tail
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
    rows: list = field(default_factory=list)   # [([cells], color)]
    info: str = ""
    scroll: int = 0


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class App:
    def __init__(self):
        self.res = None
        self.tab = TAB_SUMMARY
        self.views = [View() for _ in TABS]
        self.path_box = TextBox("Ruta del archivo MRT (o arrastre uno aquí)")
        self.as_box = TextBox("Número de AS", digits_only=True)
        self.pa_box = TextBox("Prefijo A (ej. 8.8.8.0/24)")
        self.pb_box = TextBox("Prefijo B (ej. 1.1.1.0/24)")
        self.graph_box = TextBox("Número de AS", digits_only=True)
        self.graph = None          # (root, {node: (x, y)}, edges)
        self.focus = self.path_box
        self.status = "Cargue un archivo MRT."
        self.pending = None
        self.views[TAB_SUMMARY].rows = [
            (["Cargue un archivo MRT para comenzar."], DIM)]

    # -- loading ---------------------------------------------------------
    def request_load(self, path):
        self.path_box.text = path
        self.status = f"Analizando {path} ..."
        self.pending = path

    def do_load(self, path):
        res = parse_file(path)
        self.res = res
        self.views[TAB_CONFLICTS] = View()
        self.views[TAB_EDGES] = View()
        self.views[TAB_ROUTES] = View()
        self.views[TAB_GRAPH] = View()
        self.graph = None
        self.build_summary()
        if res.ok:
            self.build_conflicts()
            self.views[TAB_EDGES].info = \
                "Escriba un número de AS y pulse Consultar."
            self.views[TAB_ROUTES].info = \
                "Escriba los prefijos A y B y pulse Consultar."
            self.views[TAB_GRAPH].info = \
                "Escriba un número de AS y pulse Consultar."
            self.status = (f"OK: {len(res.records)} registros, "
                           f"{len(res.index.conflicts)} prefijo(s) con "
                           f"más de un origen.")
            self.tab = TAB_CONFLICTS if res.index.conflicts else TAB_SUMMARY
        else:
            self.status = (f"El archivo tiene {len(res.colector.errores)} "
                           f"error(es); corríjalos para usar los análisis.")
            self.tab = TAB_SUMMARY

    # -- view construction -----------------------------------------------
    def build_summary(self):
        res, v = self.res, self.views[TAB_SUMMARY]
        rows = []
        col = res.colector
        if res.ok:
            rows.append((["Archivo analizado sin errores."], GREEN))
        else:
            rows.append((["Archivo con errores (no se habilitan los "
                          "análisis)."], RED))
        rows.append(([f"Líneas: {res.total_lines}    "
                      f"Registros válidos: {len(res.records)}    "
                      f"Errores: {len(col.errores)}    "
                      f"Advertencias: {len(col.advertencias)}"], TEXT))
        if res.ok:
            rows.append(([f"Prefijos distintos: {len(res.routing_table)}    "
                          f"AS distintos: {len(res.all_as_numbers)}    "
                          f"Aristas AS-AS: {len(res.as_graph.edges())}"],
                         TEXT))
        rows.append(([""], TEXT))
        problems = list(col.errores) + list(col.advertencias)
        for p in problems[:MAX_PROBLEMS]:
            is_error = p in col.errores
            parts = [f"Línea {p.linea}" if p.linea else "Archivo",
                     p.tipo if is_error else f"advertencia {p.tipo}"]
            if p.campo:
                parts.append(f"campo {p.campo}")
            msg = " | ".join(parts)
            if p.lexema:
                msg += f" | '{p.lexema}'"
            msg += f": {p.mensaje}"
            rows.append(([msg], RED if is_error else YELLOW))
        if len(problems) > MAX_PROBLEMS:
            rows.append(([f"... y {len(problems) - MAX_PROBLEMS} más"], DIM))
        v.rows, v.scroll = rows, 0

    def build_conflicts(self):
        idx, v = self.res.index, self.views[TAB_CONFLICTS]
        v.header = ["Prefijo", "AS origen", "Rutas", "Líneas",
                    "Ejemplo de AS path"]
        v.cols = [0, 170, 280, 350, 520]
        v.rows = []
        for prefix, by_origin in idx.conflict_rows():
            first = True
            for origin in sorted(by_origin):
                regs = by_origin[origin]
                line_nums = ",".join(str(n) for n, _ in regs[:4])
                if len(regs) > 4:
                    line_nums += ",..."
                v.rows.append(([prefix if first else "", f"AS{origin}",
                                str(len(regs)), line_nums,
                                fmt_path(regs[0][1])],
                               RED if first else YELLOW))
                first = False
        n = len(idx.conflicts)
        v.info = (f"{n} prefijo(s) reportado(s) con más de un AS origen "
                  f"(posible prefix hijacking)." if n else
                  "Ningún prefijo tiene orígenes distintos.")
        v.scroll = 0

    def build_edges(self):
        v = self.views[TAB_EDGES] = View()
        text = self.as_box.text.strip()
        if not text:
            v.info = "Escriba un número de AS."
            return
        asn = int(text)
        edge_rows = filas_aristas(self.res.index, asn)
        if not edge_rows:
            v.info = (f"El AS {asn} no aparece como peer (campo 5) en el "
                      f"archivo, así que no tiene aristas propias.")
            if asn in self.res.all_as_numbers:
                v.info += " (Sí aparece dentro de algunos AS paths.)"
            return
        v.header = ["Arista (IP del peer)", "Prefijo", "AS path", "Línea"]
        v.cols = [0, 210, 380, 900]
        ips = set()
        current_ip = None
        for ip, prefix, path, line in edge_rows:
            is_new = ip != current_ip
            current_ip = ip
            ips.add(ip)
            v.rows.append(([ip if is_new else "", prefix, path, str(line)],
                           HEADER if is_new else TEXT))
        v.info = (f"AS {asn}: {len(ips)} arista(s), {len(edge_rows)} "
                  f"prefijo(s)/ruta(s) conocidos a través de ellas.")

    def build_routes(self):
        v = self.views[TAB_ROUTES] = View()
        a = normalizar_prefijo(self.pa_box.text)
        b = normalizar_prefijo(self.pb_box.text)
        if a is None or b is None:
            v.info = ("Los prefijos deben escribirse como en el campo 6, "
                      "por ejemplo 8.8.8.0/24.")
            return
        idx = self.res.index
        missing = [p for p in (a, b) if not idx.origins_for(p)]
        if missing:
            v.info = "El prefijo " + " y ".join(missing) + \
                     " no existe en el archivo."
            return
        origins_a, origins_b, routes, truncated = routes_between_prefixes(
            self.res, a, b, MAX_ROUTE_NODES, MAX_ROUTES)
        origin_a_txt = ", ".join(f"AS{x}" for x in origins_a)
        origin_b_txt = ", ".join(f"AS{x}" for x in origins_b)
        if not routes:
            v.info = (f"No hay rutas entre {a} ({origin_a_txt}) y {b} "
                      f"({origin_b_txt}) con a lo sumo {MAX_ROUTE_NODES} AS.")
            return
        v.header = ["#", "AS", "Ruta"]
        v.cols = [0, 70, 140]
        for i, r in enumerate(routes, 1):
            v.rows.append(([str(i), str(len(r)), fmt_ruta(r)], TEXT))
        v.info = (f"{len(routes)} ruta(s) de {a} ({origin_a_txt}) a {b} "
                  f"({origin_b_txt}), sin repetir AS, máx. {MAX_ROUTE_NODES} "
                  f"AS."
                  + (f" Se muestran solo las primeras {MAX_ROUTES}."
                     if truncated else ""))

    def build_graph(self):
        v = self.views[TAB_GRAPH] = View()
        self.graph = None
        text = self.graph_box.text.strip()
        if not text:
            v.info = "Escriba un número de AS."
            return
        asn = int(text)
        nodes, edges = neighborhood(self.res.as_graph.adjacency, asn)
        if not nodes:
            v.info = f"El AS {asn} no está en el grafo."
            return
        self.graph = (asn, force_layout(nodes, edges), edges)
        v.info = (f"AS {asn}: {len(nodes)} nodo(s) y {len(edges)} "
                  f"arista(s), hasta 2 saltos.")

    # -- queries ---------------------------------------------------------
    def query(self):
        if not (self.res and self.res.ok):
            self.status = "Cargue primero un archivo sin errores."
            return
        if self.tab == TAB_EDGES:
            self.build_edges()
        elif self.tab == TAB_ROUTES:
            self.build_routes()
        elif self.tab == TAB_GRAPH:
            self.build_graph()

    # -- input -----------------------------------------------------------
    def tab_inputs(self):
        if self.tab == TAB_EDGES:
            return [self.as_box]
        if self.tab == TAB_ROUTES:
            return [self.pa_box, self.pb_box]
        if self.tab == TAB_GRAPH:
            return [self.graph_box]
        return []

    def update(self):
        # drag and drop
        try:
            if rl.is_file_dropped():
                files = rl.load_dropped_files()
                if files.count > 0:
                    p = files.paths[0]
                    if not isinstance(p, str):
                        p = rl.ffi.string(p).decode("utf-8", "replace")
                    self.request_load(p)
                rl.unload_dropped_files(files)
        except Exception:
            pass

        # focus with click
        for box in [self.path_box] + self.tab_inputs():
            if clicked(box.rect):
                self.focus = box
        if self.focus not in [self.path_box] + self.tab_inputs():
            self.focus = self.path_box

        self.focus.type_chars()
        if rl.is_key_pressed(rl.KEY_TAB):
            boxes = [self.path_box] + self.tab_inputs()
            self.focus = boxes[(boxes.index(self.focus) + 1) % len(boxes)]
        if rl.is_key_pressed(rl.KEY_ENTER) or \
                rl.is_key_pressed(rl.KEY_KP_ENTER):
            if self.focus is self.path_box:
                self.request_load(self.path_box.text.strip())
            else:
                self.query()

        # view scrolling
        v = self.views[self.tab]
        v.scroll -= int(rl.get_mouse_wheel_move() * 3)
        if rl.is_key_pressed(rl.KEY_PAGE_DOWN):
            v.scroll += 15
        if rl.is_key_pressed(rl.KEY_PAGE_UP):
            v.scroll -= 15
        if rl.is_key_pressed(rl.KEY_DOWN) or \
                rl.is_key_pressed_repeat(rl.KEY_DOWN):
            v.scroll += 1
        if rl.is_key_pressed(rl.KEY_UP) or \
                rl.is_key_pressed_repeat(rl.KEY_UP):
            v.scroll -= 1

    # -- drawing ---------------------------------------------------------
    def draw_graph(self, width, top, bottom):
        if not self.graph:
            return
        root, pos, edges = self.graph
        x0, y0 = PAD + 40, top + ROW_H + 30
        w, h = width - 2 * PAD - 80, bottom - y0 - 30

        def at(n):
            return int(x0 + pos[n][0] * w), int(y0 + pos[n][1] * h)

        for a, b in edges:
            rl.draw_line_ex(rl.Vector2(*at(a)), rl.Vector2(*at(b)), 1.5, DIM)
        for n in pos:
            px, py = at(n)
            rl.draw_circle(px, py, 9 if n == root else 6,
                           YELLOW if n == root else HEADER)
            rl.draw_text(str(n), px + 10, py - 8, FS - 4, TEXT)

    def draw(self):
        W, H = rl.get_screen_width(), rl.get_screen_height()
        rl.clear_background(BG)

        # file bar
        self.path_box.draw(PAD, 15, W - 2 * PAD - 150, 34,
                           self.focus is self.path_box)
        if button(W - PAD - 140, 15, 140, 34, "Cargar"):
            self.request_load(self.path_box.text.strip())

        # tabs
        tw = (W - 2 * PAD) // len(TABS)
        for i, name in enumerate(TABS):
            r = rl.Rectangle(PAD + i * tw, 60, tw - 4, 32)
            rl.draw_rectangle_rec(r, TAB_ON if i == self.tab else TAB_OFF)
            lw = rl.measure_text(name, FS)
            rl.draw_text(name, int(r.x + (r.width - lw) / 2), 67, FS, TEXT)
            if clicked(r):
                self.tab = i

        # tab-specific inputs
        y = 102
        if self.tab == TAB_EDGES:
            self.as_box.draw(PAD, y, 300, 34, self.focus is self.as_box)
            if button(PAD + 312, y, 140, 34, "Consultar"):
                self.query()
            y += 46
        elif self.tab == TAB_ROUTES:
            w = (W - 2 * PAD - 160) // 2
            self.pa_box.draw(PAD, y, w, 34, self.focus is self.pa_box)
            self.pb_box.draw(PAD + w + 8, y, w, 34, self.focus is self.pb_box)
            if button(W - PAD - 140, y, 140, 34, "Consultar"):
                self.query()
            y += 46
        elif self.tab == TAB_GRAPH:
            self.graph_box.draw(PAD, y, 300, 34,
                                self.focus is self.graph_box)
            if button(PAD + 312, y, 140, 34, "Consultar"):
                self.query()
            y += 46

        # results panel
        v = self.views[self.tab]
        bottom = H - 36
        rl.draw_rectangle(PAD, y, W - 2 * PAD, bottom - y, PANEL)
        cy = y + 6
        if v.info:
            rl.draw_text(clip_text(safe(v.info), W - 2 * PAD - 16),
                         PAD + 8, cy, FS, DIM)
            cy += ROW_H + 4
        if v.header:
            for c, h in zip(v.cols, v.header):
                rl.draw_text(safe(h), PAD + 8 + c, cy, FS, HEADER)
            cy += ROW_H + 2
            rl.draw_line(PAD + 8, cy - 2, W - PAD - 8, cy - 2, DIM)
        visible = max(1, int((bottom - cy - 4) // ROW_H))
        v.scroll = max(0, min(v.scroll, max(0, len(v.rows) - visible)))
        for i in range(v.scroll, min(len(v.rows), v.scroll + visible)):
            cells, color = v.rows[i]
            for j, cell in enumerate(cells):
                x = PAD + 8 + v.cols[min(j, len(v.cols) - 1)]
                if j + 1 < len(v.cols):
                    width = v.cols[j + 1] - v.cols[j] - 10
                else:
                    width = W - PAD - 8 - x
                rl.draw_text(clip_text(safe(cell), width), x, cy, FS, color)
            cy += ROW_H
        if len(v.rows) > visible:
            rl.draw_text(
                f"{v.scroll + 1}-{min(len(v.rows), v.scroll + visible)}"
                f" de {len(v.rows)}", W - PAD - 130, y + 6, FS - 2, DIM)

        if self.tab == TAB_GRAPH:
            self.draw_graph(W, y, bottom)

        # status bar
        rl.draw_text(clip_text(safe(self.status), W - 2 * PAD), PAD, H - 28,
                     FS, DIM)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rl.set_config_flags(rl.FLAG_WINDOW_RESIZABLE)
    rl.init_window(1100, 700, "Analizador MRT - Rutas en Internet")
    rl.set_window_min_size(800, 500)
    rl.set_target_fps(60)
    app = App()
    if argv:
        app.request_load(argv[0])
    while not rl.window_should_close():
        if app.pending is not None:
            path, app.pending = app.pending, None
            app.do_load(path)
        app.update()
        rl.begin_drawing()
        app.draw()
        rl.end_drawing()
    rl.close_window()


if __name__ == "__main__":
    main()