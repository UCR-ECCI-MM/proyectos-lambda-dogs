### Gramática a utilizar.

```text
Linea      → RECORD_TYPE PIPE TIMESTAMP PIPE STATE PIPE IPADDR PIPE NUMBER PIPE Prefijo PIPE ASPath

Prefijo    → IPADDR SLASH NUMBER

ASPath     → ASPath ASElemento
           | ASElemento

ASElemento → NUMBER
           | LBRACE ASSet RBRACE

ASSet      → ASSet COMMA NUMBER
           | NUMBER
```