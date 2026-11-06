from core import *

inst = generar_instancia(10, semilla=1)
print("W =", inst.capacidad, "| umbrales =", inst.umbrales)

x = [1, 0, 1, 0, 0, 1, 0, 0, 0, 0]
print("peso:", peso_total(inst, x))
print("props:", props_totales(inst, x))
print("Z:", potencia(inst, x))
print("válida:", es_valida(inst, x))

guardar_instancia(inst, "instancias/n10_s1.json")
assert cargar_instancia("instancias/n10_s1.json").capacidad == inst.capacidad
print("OK")