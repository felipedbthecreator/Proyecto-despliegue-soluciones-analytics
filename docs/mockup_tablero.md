# Mockup del tablero

## Flujo principal

1. La persona usuaria selecciona municipio, cultivo y variante.
2. Selecciona un escenario climático: Niño, neutro o Niña.
3. El tablero consulta la API y muestra el rendimiento esperado en t/ha.
4. Como contexto, muestra históricos de área cosechada, producción y rendimiento.
5. Un aviso indica que la predicción es una estimación y no reemplaza la planeación técnica.

## Distribución propuesta

```text
+---------------------------------------------------------------+
| Rendimiento agrícola esperado                                 |
| Municipio [Bogotá       v] Cultivo [Arroz v] Variante [Riego]|
| Escenario [Niño v]                 [Consultar predicción]     |
+---------------------------------------------------------------+
| Rendimiento esperado: 4.8 t/ha       Intervalo: 4.2 - 5.3   |
| Comparación: -12% frente al periodo anterior                 |
+---------------------------------------------------------------+
| Histórico de rendimiento                 | Área y producción |
| [gráfico por periodo]                     | [gráfico doble]  |
+---------------------------------------------------------------+
| Nota: la señal climática y sus fuentes se documentarán...    |
+---------------------------------------------------------------+
```

La hipótesis de arroz de riego frente a arroz de secano se visualizará
comparando las dos variantes en el mismo municipio y periodo.
