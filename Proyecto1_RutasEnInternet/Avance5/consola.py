"""
Aplicación de consola (respaldo de la GUI): las tres funcionalidades de la
sección 4 del enunciado.

    python consola.py archivo.txt            # menú interactivo
    python consola.py archivo.txt --origenes # funcionalidad 1 y termina
    python consola.py archivo.txt --as 53046 # funcionalidad 2 y termina
    python consola.py archivo.txt --rutas 7.0.0.0/8 8.8.8.0/24   # func. 3
"""

import argparse
import sys

from parser import parse_file, build_report
from display import C, draw_table
from analysis import (fmt_path, fmt_ruta, filas_aristas, normalizar_prefijo,
                      routes_between_prefixes)

MAX_NODOS_RUTA = 12
MAX_RUTAS = 1000


def funcionalidad_1(res):
    filas = []
    for prefijo, por_origen in res.index.conflict_rows():
        primero = True
        for origen in sorted(por_origen):
            regs = por_origen[origen]
            filas.append([prefijo if primero else '', f"AS{origen}",
                          len(regs), fmt_path(regs[0][1])])
            primero = False
    if not filas:
        print(f"{C.GREEN}Ningún prefijo tiene más de un AS origen.{C.RESET}")
        return
    print("\n".join(draw_table(
        ["Prefijo", "AS origen", "Rutas", "Ejemplo de AS path"], filas,
        title=f"POSIBLE PREFIX HIJACKING: {len(res.index.conflicts)} "
              f"prefijo(s) con más de un origen", title_color=C.RED)))


def funcionalidad_2(res, asn):
    filas = filas_aristas(res.index, asn)
    if not filas:
        print(f"El AS {asn} no aparece como peer (campo 5) en el archivo, "
              f"así que no tiene aristas propias.")
        return
    mostrar, ip_prev = [], None
    for ip, prefijo, path, _ in filas:
        mostrar.append([ip if ip != ip_prev else '', prefijo, path])
        ip_prev = ip
    print("\n".join(draw_table(["Arista (IP del peer)", "Prefijo", "AS path"],
                               mostrar, title=f"ARISTAS DEL AS {asn}")))


def funcionalidad_3(res, a_txt, b_txt):
    a, b = normalizar_prefijo(a_txt), normalizar_prefijo(b_txt)
    if a is None or b is None:
        print("Los prefijos deben escribirse como en el campo 6, por ejemplo "
              "8.8.8.0/24.")
        return
    faltan = [p for p in (a, b) if not res.index.origins_for(p)]
    if faltan:
        print("El prefijo " + " y ".join(faltan) + " no existe en el archivo.")
        return
    oa, ob, rutas, truncado = routes_between_prefixes(
        res, a, b, MAX_NODOS_RUTA, MAX_RUTAS)
    if not rutas:
        print(f"No hay rutas entre {a} y {b} (máx. {MAX_NODOS_RUTA} AS).")
        return
    print("\n".join(draw_table(
        ["#", "AS", "Ruta"],
        [[i, len(r), fmt_ruta(r)] for i, r in enumerate(rutas, 1)],
        title=f"RUTAS de {a} (AS{', AS'.join(map(str, oa))}) a {b} "
              f"(AS{', AS'.join(map(str, ob))})")))
    print(f"{len(rutas)} ruta(s), sin repetir AS, máx. {MAX_NODOS_RUTA} AS."
          + (f" Truncado a {MAX_RUTAS}." if truncado else ""))


def menu(res):
    while True:
        print("\n1) Prefijos con más de un AS origen   2) Aristas de un AS\n"
              "3) Rutas entre dos prefijos            0) Salir")
        try:
            op = input("> ").strip()
            if op == '1':
                funcionalidad_1(res)
            elif op == '2':
                txt = input("Número de AS: ").strip()
                if txt.isdigit():
                    funcionalidad_2(res, int(txt))
                else:
                    print("Debe ser un número.")
            elif op == '3':
                funcionalidad_3(res, input("Prefijo A: "), input("Prefijo B: "))
            elif op == '0':
                return
        except (EOFError, KeyboardInterrupt):
            return


def main(argv=None):
    ap = argparse.ArgumentParser(description="Consultas sobre un dump MRT.")
    ap.add_argument("archivo")
    ap.add_argument("--origenes", action="store_true")
    ap.add_argument("--as", dest="asn", type=int)
    ap.add_argument("--rutas", nargs=2, metavar=("A", "B"))
    args = ap.parse_args(argv)

    res = parse_file(args.archivo)
    if not res.ok:
        print("\n".join(build_report(res)))
        return 1
    print(f"{C.GREEN}Archivo correcto:{C.RESET} {len(res.records)} registros, "
          f"{len(res.routing_table)} prefijos, {len(res.all_as_numbers)} AS.")
    if args.origenes:
        funcionalidad_1(res)
    elif args.asn is not None:
        funcionalidad_2(res, args.asn)
    elif args.rutas:
        funcionalidad_3(res, *args.rutas)
    else:
        menu(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
