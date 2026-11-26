# Proyecto 2 · El Alquimista de Pociones

**Curso:** CI-0124 Computabilidad y Complejidad · II-2026 · Prof. Maureen Murillo Rivera
**Equipo:** Lambda Dogs — Gabriel Coto Fernández, May Retana Delgado, Isaac Araya Quesada

## El problema
Mochila 0/1 multidimensional (NP-duro): dado un conjunto de N ingredientes con peso y tres propiedades
(fuerza, sigilo, maná), elegir la receta que maximiza la potencia Z sin exceder la capacidad del caldero
y cumpliendo un umbral mínimo por propiedad. Las instancias se generan con semilla fija (reproducibles).

## Técnicas implementadas
| Técnica | Archivo | Función principal |
|---|---|---|
| Fuerza bruta (óptimo exacto, O(N·2^N)) | `fuerzabruta.py` | `fuerzabruta(inst)` |
| Heurística: regla del alquimista experto (simple y con reparación) | `heuristica.py` | `heuristica_simple`, `heuristica_reparacion` |
| Metaheurística: algoritmo genético | `genetico.py` | `algoritmo_genetico(inst, params, semilla)` |

## Estructura
```
core.py             Instancia, validación, potencia, violación, generador y carga/guardado
fuerzabruta.py      Fuerza bruta
heuristica.py       Heurística simple y con reparación
genetico.py         Algoritmo genético (torneo, cruce de un punto, mutación, elitismo)
calibracion_ga.py   Barrido de parámetros del genético (fase 1 y fase 2)
experimentos.py     Experimentos y gráficos del análisis
pruebacore.py       Prueba rápida del núcleo
instancias/         Instancias de ejemplo (JSON)
resultados/         CSV y figuras generados por los experimentos
propuesta_y_bitacora/  Propuesta, bitácora y documentos de entrega
```

## Requisitos
- Python 3.10 o superior
- `matplotlib` (solo para `experimentos.py`): `pip install matplotlib`

## Cómo ejecutar
Desde la carpeta del proyecto:

```bash
# Cada técnica por separado (demo en consola)
python fuerzabruta.py
python heuristica.py
python genetico.py

# Calibración de parámetros del genético (tarda varios minutos)
python calibracion_ga.py

# Experimentos del análisis (generan CSV y figuras en resultados/)
python experimentos.py tiempo          # fuerza bruta: tiempo vs. N
python experimentos.py comparacion     # 3 técnicas, N = 10..18, óptimo conocido
python experimentos.py escalabilidad   # heurística vs. genético, N = 20..400
python experimentos.py convergencia    # convergencia del genético (N = 40)
python experimentos.py todo            # todos los anteriores
```

Uso desde código:
```python
from core import generar_instancia
from heuristica import heuristica_reparacion
from genetico import algoritmo_genetico

inst = generar_instancia(20, semilla=42)
x, z, t, historial = algoritmo_genetico(inst, semilla=0)
```

## Notas
- La fuerza bruta es inviable para N > ~25 (≈22 s en N = 22; el tiempo se duplica por ingrediente).
- Los parámetros finales del genético (población 100, pc 0.9, pm = 1/N, torneo 3, elitismo 2,
  penalización 10) están documentados en el documento de análisis.
- Los resultados dependen de las semillas; con las mismas semillas se reproducen los mismos datos.
