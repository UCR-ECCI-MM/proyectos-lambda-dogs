# Gramática (Avance 5)

> Los números se clasifican en el **lexer** solo por cantidad de dígitos
> (`NUM10` = exactamente 10, `NUM9` = de 1 a 9); la gramática decide, según
> la posición, si es timestamp, peer AS, máscara o AS del path (ver Avance 4).

## Cambios respecto al Avance 4

- **`NEWLINE` es terminal**: cada registro termina con un salto de línea, así
  una línea = un registro (antes los saltos se ignoraban y un registro
  partido en dos líneas, o dos en una, se aceptaba).
- **Recuperación de errores**: `item → error NEWLINE` descarta la línea mala
  y el análisis continúa, para reportar todos los errores del archivo.
- **Recursión por la izquierda** en la lista de líneas (la pila ya no crece
  con el número de líneas).
- **`INICIO`** es un token sintético que el lexer emite al comenzar el
  archivo. Se necesita para que la recuperación de errores funcione también
  cuando el primer token del archivo es inválido.
- **`ILLEGAL`** es un token que el lexer devuelve para un lexema inválido
  (IP mal formada, número con ceros a la izquierda, etc.). No aparece en
  ninguna producción: al llegar al parser provoca la recuperación de errores.

## Especificación formal

```text
G = {V, T, A, S}

V = { archivo, lista, item, linea, timestamp, peer_as, prefix, mask,
      as_path, as_element, as_num, as_set, as_set_list }

T = { INICIO, RECORD_TYPE, PIPE, STATE, IPADDR, SLASH, NUM10, NUM9,
      LBRACE, RBRACE, COMMA, NEWLINE }
    (más ILLEGAL, que el lexer emite pero no aparece en la gramática)

S = archivo
```

## Producciones

```text
archivo     → INICIO lista
lista       → lista item | item
item        → linea | error NEWLINE

linea       → RECORD_TYPE PIPE timestamp PIPE STATE PIPE IPADDR PIPE
              peer_as PIPE prefix PIPE as_path NEWLINE

timestamp   → NUM10
peer_as     → NUM10 | NUM9
prefix      → IPADDR SLASH mask
mask        → NUM9

as_path     → as_element as_path | as_element
as_element  → as_num | as_set
as_num      → NUM10 | NUM9
as_set      → LBRACE as_set_list RBRACE
as_set_list → as_num COMMA as_set_list | as_num
```

## Validaciones semánticas (en la acción de `linea`)

| Validación | Resultado |
|---|---|
| El AS path debe **comenzar** con el peer AS (si el primer elemento es un `{...}`, el peer debe estar dentro) | error, el registro se descarta |
| Máscara mayor a 32 | error, el registro se descarta |
| Máscara 0 o 32 (fuera del 1–31 del enunciado, pero válidas en CIDR) | **advertencia**, el registro se acepta |
