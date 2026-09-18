# Gramática

> Nota: esta gramática reemplaza la versión original del enunciado, que
> definía los terminales `TIMESTAMP`, `PEER_AS`, `MASK` y `AS_PATH_NUM` como
> tokens distintos del lexer. Eso resultaba ambiguo: un `TIMESTAMP` y un
> `PEER_AS` pueden tener ambos 10 dígitos, y el lexer no conoce la posición
> del campo dentro de la línea para diferenciarlos. La corrección de la
> profesora (14 de setiembre) fue que esa diferenciación debe resolverse en
> el lexer, no en el parser. La solución adoptada: el lexer clasifica los
> números solo por cantidad de dígitos (`NUM10` exactamente 10 dígitos,
> `NUM9` de 1 a 9 dígitos), y es la gramática la que, según la posición,
> decide si un `NUM10`/`NUM9` es un timestamp, un peer_as, una máscara o un
> elemento de AS_PATH.

## Especificación formal de la gramática

```text
Se define la gramatica G={V,T,A,S} de la siguiente manera:

Variables (no terminales, en minúscula por convención del curso)

V = { archivo, linea, timestamp, peer_as, prefix, mask,
      as_path, as_element, as_num, as_set, as_set_list }

Terminales
T = { RECORD_TYPE, PIPE, STATE, IPADDR, SLASH, NUM10, NUM9,
      LBRACE, RBRACE, COMMA }

Simbolo inicial S = archivo
```

## Gramática a utilizar

```text

archivo → linea archivo

archivo → linea

linea → RECORD_TYPE PIPE timestamp PIPE STATE
        PIPE IPADDR PIPE peer_as PIPE prefix
        PIPE as_path

timestamp → NUM10

peer_as → NUM10

peer_as → NUM9

prefix → IPADDR SLASH mask

mask → NUM9

as_path → as_element as_path

as_path → as_element

as_element → as_num

as_element → as_set

as_num → NUM10

as_num → NUM9

as_set → LBRACE as_set_list RBRACE

as_set_list → as_num COMMA as_set_list

as_set_list → as_num
```

## Regla semántica adicional

Además de la estructura sintáctica, la acción de `linea` valida que el
`peer_as` reportado en el campo 5 coincida con algún elemento del `as_path`
del campo 7 (reportado como error semántico si no es así).
