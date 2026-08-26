<div align="center">

# 🐾 Lambda Dogs

### Repositorio de proyectos — Computabilidad y Complejidad (CI0124)

![Status](https://img.shields.io/badge/estado-en%20progreso-yellow?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![PLY](https://img.shields.io/badge/PLY-Lex%20%26%20Yacc-blueviolet?style=flat-square)
![Course](https://img.shields.io/badge/curso-CI0124-informational?style=flat-square)
![Semester](https://img.shields.io/badge/semestre-II--2026-lightgrey?style=flat-square)

</div>

---
## 👥 Equipo

| Nombre | Carné |
|---|---|
| May Retana Delgado | C16409 |
| Gabriel Coto Fernández | C4E540 |
| Isaac Araya Quesada | C4C567 |

**Curso:** Computabilidad y Complejidad – CI0124 · **Profesora:** Maureen Murillo R. · **Semestre:** II-2026

---

## 📡 Proyecto 1 — Rutas en Internet (Parser de dumps MRT/BGP)

Un analizador léxico y sintáctico, construido con **PLY (Python Lex-Yacc)**, que valida archivos de dump **MRT** (`TABLE_DUMP2`) generados a partir de anuncios **BGP**, y una aplicación que explota esa información para detectar anomalías de enrutamiento (posible *prefix hijacking*), listar las rutas de un AS y encontrar todas las rutas entre dos prefijos.

```
TABLE_DUMP2|1785888000|B|177.101.16.80|53046|7.0.0.0/8|53046 61626 14840 3356 749
```

### 📁 Estructura

```
Proyecto1_RutasEnInternet/
├── Avance1/   → Diagrama de conceptos + diseño de estructuras de datos (PDF)
├── Avance2/   → Analizador léxico (lexer.py) funcionando
└── Avance3/   → Analizador sintáctico (en curso)
Chunks/        → Archivos de prueba (dumps MRT de ejemplo)
```

### ✅ Avance del proyecto

| Etapa | Entregable | Peso | Estado | Fecha |
|---|---|---|---|---|
| 1 | Diagrama de conceptos + diseño de estructuras de datos | 10% | ✅ Completo | 20 ago |
| 2 | Analizador léxico | 20% | ✅ Completo | 24 ago |
| 3 | Analizador sintáctico (sin crear estructuras) | 35% | 🚧 En progreso | 14 set |
| 4 | Creación dinámica de estructuras de datos | 15% | ⬜ Pendiente | 21 set |
| 5 | Aplicación completa | 20% | ⬜ Pendiente | 5 oct |

### 🔤 Analizador léxico

El lexer (`lexer.py`) reconoce los 7 campos de cada línea del dump y valida, entre otros:
- `TABLE_DUMP2` como tipo de registro
- Timestamp de 10 dígitos (uint32)
- Estado `B`, `A` o `W`
- Direcciones IPv4 válidas (octetos 0–255)
- Máscara de red entre 0 y 32
- Números de AS dentro del rango de 32 bits

Ejecución:

```bash
python lexer.py <archivo_dump.txt>
```

### 🛠️ Tecnologías

- Python 3
- [PLY](https://www.dabeaz.com/ply/) (Python Lex-Yacc)