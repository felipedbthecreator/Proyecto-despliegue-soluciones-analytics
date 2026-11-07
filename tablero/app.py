"""Tablero: rendimiento agrícola esperado (arroz, papa y caña) bajo El Niño, neutro y La Niña.

Ejecutar:  python app.py   ->  http://localhost:8050
Variables de entorno opcionales: API_URL, RUTA_DATASET, RUTA_RONI, PUERTO.
"""
import json
import os

import dash
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html

import cliente_api
import datos
from config import API_URL, COLORES, CULTIVOS, ESCENARIOS, VARIANTES

ESC = list(ESCENARIOS)  # ["nino", "neutro", "nina"]
NOMBRE_ESC = {k: v["etiqueta"] for k, v in ESCENARIOS.items()}
FASE_A_ESC = {"El Niño": "nino", "Neutro": "neutro", "La Niña": "nina"}
COLOR_ESC = {"nino": COLORES["nino"], "neutro": COLORES["neutro"], "nina": COLORES["nina"]}
FASE = datos.fase_actual()
DEPTO_INICIAL, MPIO_INICIAL, VARIANTE_INICIAL = "Córdoba", 23570, "secano_man"  # Pueblo Nuevo


# ---------------------------------------------------------------- utilidades
def fmt(x: float, d: int = 1) -> str:
    """Formato colombiano: punto para miles y coma para decimales."""
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def decimales(variante: str) -> int:
    return 0 if VARIANTES[variante]["cultivo"] == "cana" else 1


def pct(x: float) -> str:
    signo = "+" if x > 0.0005 else "−" if x < -0.0005 else ""
    return f"{signo}{fmt(abs(x) * 100, 1)} %"


def layout_fig(fig: go.Figure, alto: int) -> go.Figure:
    fig.update_layout(height=alto, margin=dict(l=8, r=8, t=8, b=8), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                      font=dict(family="Libre Franklin, Helvetica Neue, Arial", size=12, color=COLORES["tinta"]),
                      separators=",.")
    fig.update_xaxes(gridcolor=COLORES["linea"], zeroline=False, linecolor=COLORES["linea"])
    fig.update_yaxes(gridcolor=COLORES["linea"], zeroline=False, linecolor=COLORES["linea"])
    return fig


def campo(etiqueta: str, control) -> html.Div:
    return html.Div([html.Span(etiqueta, className="lbl"), control], className="field")


# ---------------------------------------------------------------- layout
app = dash.Dash(__name__, title="Rendimiento agrícola esperado bajo El Niño",
                external_stylesheets=["https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700;800&display=swap"])
server = app.server  # para gunicorn en el despliegue con Docker

estado_inicial = cliente_api.probar_conexion(API_URL)

app.layout = html.Div([
    dcc.Store(id="estado-api", data=estado_inicial),

    html.Header([
        html.Div([html.H1("Rendimiento agrícola esperado"),
                  html.Span("Arroz, papa y caña por municipio y escenario climático")], className="brand"),
        html.Div([html.Span(className=f"phase-dot {FASE['fase']}"),
                  html.Span(["Fase actual: ", html.Strong(NOMBRE_ESC[FASE["fase"]]),
                             f" (RONI {FASE['trimestre']} {FASE['anio']}: {fmt(FASE['valor'], 2)})"])],
                 className="phase-pill", title="Fase según el último trimestre publicado del RONI (NOAA/CPC); umbral ±0,5"),
    ], className="topbar"),
    html.Div(id="banner-fuente", className="source-banner"),

    html.Div([
        # ---------------- Panel de consulta ----------------
        html.Aside([
            html.H2("Consulta"),
            html.P("Elija el municipio, el cultivo y el periodo a estimar.", className="sub"),
            campo("Departamento", dcc.Dropdown(id="depto", options=datos.departamentos(),
                                               value=DEPTO_INICIAL, clearable=False)),
            campo("Municipio", dcc.Dropdown(id="mpio", clearable=False)),
            campo("Cultivo", dcc.RadioItems(id="cultivo", className="seg", inputStyle={})),
            campo("Variante", dcc.Dropdown(id="variante", clearable=False)),
            campo("Periodo a estimar", dcc.Dropdown(id="periodo", clearable=False)),
            html.Button("Calcular rendimiento esperado", id="calcular", className="btn-primary"),
            html.P("Solo se usa información conocida antes de la cosecha: municipio, cultivo, variante, "
                   "periodo y fase de El Niño. No se usan área cosechada ni producción.", className="hint"),

            html.Div([
                html.H3("Conexión con la API del modelo"),
                html.Div(id="api-badge"),
                html.Div([dcc.Input(id="api-url", type="url", value=API_URL,
                                    placeholder="http://<ip-ec2>:8001", debounce=True),
                          html.Button("Probar", id="api-probar", className="btn-sec")], className="api-row"),
                html.Div("Petición POST /predict (una por escenario):"),
                html.Pre(id="api-peticion"),
            ], className="api-box"),
        ], className="panel panel-pad filters"),

        # ---------------- Contenido principal ----------------
        html.Main([
            html.P(id="contexto", className="context-line"),

            html.Section([
                html.H2("Rendimiento esperado según el escenario climático"),
                html.P("Estimación en t/ha con intervalo de predicción del 80%.", className="sub"),
                html.Div(id="tarjetas", className="scen-grid"),
                dcc.Graph(id="fig-rangos", config={"displayModeBar": False}),
                html.P(id="mensaje", className="insight"),
            ], className="panel panel-pad"),

            html.Section(id="kpis", className="kpis"),

            html.Div([
                html.Section([
                    html.H2("Rendimiento histórico del municipio"),
                    html.P("Rendimiento observado por periodo (EVA 2019–2025) con la fase del RONI sombreada. "
                           "La línea punteada es la mediana nacional de la variante.", className="sub"),
                    dcc.Graph(id="fig-historia", config={"displayModeBar": False}),
                ], className="panel panel-pad"),
                html.Section([
                    html.H2("Variantes del cultivo"),
                    html.P(id="sub-variantes", className="sub"),
                    dcc.Graph(id="fig-variantes", config={"displayModeBar": False}),
                ], className="panel panel-pad"),
            ], className="two-col"),

            html.Section([
                html.H2("Municipios del departamento más sensibles a El Niño"),
                html.P(id="sub-ranking", className="sub"),
                html.Ul(id="ranking", className="rank"),
            ], className="panel panel-pad"),

            html.P([html.Strong("Cómo leer estas cifras. "),
                    "El tablero compara escenarios: no pronostica el clima ni garantiza que la diferencia se deba solo "
                    "al clima. Entre 2019 y 2025 hubo dos semestres de El Niño (2019A y 2023B) y ningún año completo "
                    "en esa fase, por lo que en caña el escenario de El Niño se estima con menos información. "
                    "Fuentes: EVA 2019–2025 (UPRA, datos.gov.co) e índice RONI (NOAA/CPC)."], className="note"),
        ], className="main"),
    ], className="layout"),
])


# ---------------------------------------------------------------- filtros encadenados
@app.callback(Output("mpio", "options"), Output("mpio", "value"), Input("depto", "value"))
def actualizar_municipios(depto):
    opciones = datos.municipios(depto)
    valores = [o["value"] for o in opciones]
    return opciones, MPIO_INICIAL if MPIO_INICIAL in valores else valores[0]


@app.callback(Output("cultivo", "options"), Output("cultivo", "value"), Input("mpio", "value"), State("cultivo", "value"))
def actualizar_cultivos(mpio, actual):
    disponibles = datos.cultivos_municipio(mpio)
    opciones = [{"label": CULTIVOS[c]["etiqueta"], "value": c, "disabled": c not in disponibles} for c in CULTIVOS]
    return opciones, actual if actual in disponibles else disponibles[0]


@app.callback(Output("variante", "options"), Output("variante", "value"),
              Output("periodo", "options"), Output("periodo", "value"),
              Input("mpio", "value"), Input("cultivo", "value"), State("variante", "value"))
def actualizar_variantes(mpio, cultivo, actual):
    vs = datos.variantes_municipio(mpio, cultivo)
    preferida = VARIANTE_INICIAL if actual is None else actual
    periodos = CULTIVOS[cultivo]["periodos"]
    return ([{"label": VARIANTES[v]["etiqueta"], "value": v} for v in vs], preferida if preferida in vs else vs[0],
            periodos, periodos[0])


# ---------------------------------------------------------------- conexión con la API
@app.callback(Output("estado-api", "data"), Input("api-probar", "n_clicks"), Input("api-url", "value"),
              prevent_initial_call=True)
def conectar_api(_, url):
    return cliente_api.probar_conexion(url)


@app.callback(Output("api-badge", "children"), Output("banner-fuente", "children"),
              Output("banner-fuente", "className"), Input("estado-api", "data"))
def mostrar_estado_api(estado):
    if estado.get("conectada"):
        return (html.Span(estado["mensaje"], className="badge on"),
                f"Predicciones servidas por la API del modelo ({estado['url']}).", "source-banner api")
    return (html.Span(f"No conectada · {estado['mensaje']}", className="badge off"),
            "API del modelo aún no conectada: las cifras de los escenarios son una estimación provisional local "
            "(línea base del municipio ajustada por su sensibilidad histórica al RONI), no el modelo seleccionado.",
            "source-banner")


# ---------------------------------------------------------------- figuras
def fig_rangos(pred: dict, d: int) -> go.Figure:
    fig = go.Figure()
    for i, esc in enumerate(ESC):
        p = pred[esc]
        lo, hi = p["intervalo_80"]
        fig.add_trace(go.Scatter(x=[lo, hi], y=[NOMBRE_ESC[esc]] * 2, mode="lines",
                                 line=dict(color=COLOR_ESC[esc], width=10), opacity=0.35, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[p["rendimiento_t_ha"]], y=[NOMBRE_ESC[esc]], mode="markers",
                                 marker=dict(color=COLOR_ESC[esc], size=14, line=dict(color="white", width=2)),
                                 hovertemplate=f"{NOMBRE_ESC[esc]}: %{{x:.{d}f}} t/ha "
                                               f"(80%: {fmt(lo, d)} – {fmt(hi, d)})<extra></extra>"))
    fig.update_yaxes(categoryorder="array", categoryarray=[NOMBRE_ESC[e] for e in reversed(ESC)], showgrid=False)
    fig.update_xaxes(title_text="t/ha", tickformat=f".{d}f")
    return layout_fig(fig, 170)


def fig_historia(h, nat: float, d: int) -> go.Figure:
    fig = go.Figure()
    periodos = h["periodo"].tolist()
    for i, r in enumerate(h.itertuples()):
        esc = FASE_A_ESC.get(r.fase, "neutro")
        if esc != "neutro":
            fig.add_vrect(x0=i - 0.5, x1=i + 0.5, fillcolor=COLORES[f"{esc}_suave"], line_width=0, layer="below")
    fig.add_hline(y=nat, line=dict(color=COLORES["tenue"], dash="dash", width=1.5),
                  annotation_text=f"Mediana nacional {fmt(nat, d)}", annotation_position="top left",
                  annotation_font=dict(size=11, color=COLORES["tenue"]))
    fig.add_trace(go.Scatter(x=list(range(len(h))), y=h["rendimiento"], mode="lines+markers",
                             line=dict(color=COLORES["primario"], width=2.5), marker=dict(size=7),
                             customdata=list(zip(periodos, h["fase"])),
                             hovertemplate="%{customdata[0]} (%{customdata[1]}): %{y:." + str(d) + "f} t/ha<extra></extra>"))
    fig.update_xaxes(tickmode="array", tickvals=list(range(len(h))), ticktext=periodos, showgrid=False,
                     range=[-0.5, len(h) - 0.5], tickangle=0, tickfont=dict(size=10))
    fig.update_yaxes(title_text="t/ha", rangemode="tozero")
    return layout_fig(fig, 290)


def fig_variantes(filas: list[dict], seleccionada: str, d: int) -> go.Figure:
    fig = go.Figure()
    etiquetas = [VARIANTES[f["v"]]["etiqueta"] + ("" if f["local"] else "<br><sub>mediana nacional</sub>") for f in filas]
    for esc in reversed(ESC):
        vals = [f["pred"][esc] for f in filas]
        fig.add_trace(go.Bar(y=etiquetas, x=vals, orientation="h", name=NOMBRE_ESC[esc],
                             marker=dict(color=COLOR_ESC[esc], opacity=[1 if f["local"] else 0.45 for f in filas]),
                             text=[fmt(v, d) for v in vals], textposition="outside", cliponaxis=False,
                             textfont=dict(size=11, color=COLORES["tenue"]),
                             hovertemplate=f"{NOMBRE_ESC[esc]}: %{{x:.{d}f}} t/ha<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05)
    fig.update_xaxes(showgrid=True, ticksuffix=" t/ha" if d == 0 else "")
    fig = layout_fig(fig, max(240, 95 * len(filas) + 40))
    fig.update_layout(showlegend=True, margin=dict(r=40, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, traceorder="reversed"))
    return fig


# ---------------------------------------------------------------- render principal
@app.callback(
    Output("contexto", "children"), Output("api-peticion", "children"),
    Output("tarjetas", "children"), Output("fig-rangos", "figure"), Output("mensaje", "children"),
    Output("kpis", "children"), Output("fig-historia", "figure"),
    Output("sub-variantes", "children"), Output("fig-variantes", "figure"),
    Output("sub-ranking", "children"), Output("ranking", "children"),
    Input("calcular", "n_clicks"), Input("variante", "value"), Input("periodo", "value"), Input("estado-api", "data"),
    State("mpio", "value"), State("cultivo", "value"),
)
def render(_, variante, periodo, estado_api, mpio, cultivo):
    if not (variante and periodo and mpio) or VARIANTES[variante]["cultivo"] != cultivo:
        raise dash.exceptions.PreventUpdate
    municipio, depto = datos.nombre_municipio(mpio)
    d = decimales(variante)
    etiqueta_var = VARIANTES[variante]["etiqueta"]
    etiqueta_cult = CULTIVOS[cultivo]["etiqueta"]
    txt_cultivo = etiqueta_var if cultivo == "cana" else f"{etiqueta_cult} {etiqueta_var.lower()}"

    pred, fuente = cliente_api.predecir_escenarios(estado_api, mpio, municipio, cultivo, variante, periodo)
    contexto = ["Consulta: ", html.Strong(f"{municipio}, {depto}"), f". {txt_cultivo}, periodo {periodo}. ",
                html.Span(f"Fuente de la estimación: {'API · ' + pred['neutro']['modelo'] if fuente == 'api' else 'provisional local'}.")]
    peticion = json.dumps(cliente_api.armar_peticion(mpio, municipio, cultivo, variante, periodo, "nino|neutro|nina"),
                          ensure_ascii=False, indent=1)

    # ---- Tarjetas de escenario
    y_neu = pred["neutro"]["rendimiento_t_ha"]
    tarjetas = []
    for esc in ESC:
        p = pred[esc]
        y, (lo, hi) = p["rendimiento_t_ha"], p["intervalo_80"]
        dif = (y - y_neu) / y_neu
        if esc == "neutro":
            clase, texto = "flat", "Escenario de referencia"
        elif abs(dif) < 0.005:
            clase, texto = "flat", "Sin diferencia apreciable frente a neutro"
        else:
            clase = "down" if dif < 0 else "up"
            texto = f"{pct(dif)} frente a neutro ({'−' if dif < 0 else '+'}{fmt(abs(y - y_neu), d)} t/ha)"
        vigente = esc == FASE["fase"]
        tarjetas.append(html.Article([
            html.H3([NOMBRE_ESC[esc], html.Span("Fase vigente", className="tag") if vigente else None]),
            html.P([fmt(y, d), html.Small("t/ha")], className="val"),
            html.P(f"Intervalo 80%: {fmt(lo, d)} – {fmt(hi, d)}", className="ci"),
            html.P(texto, className=f"delta {clase}"),
            html.P(p["advertencia"], className="warn") if p.get("advertencia") else None,
        ], className=f"scen {esc} {'current' if vigente else ''}"))

    # ---- Mensaje en toneladas
    area, per_area = datos.ultima_area_sembrada(mpio, variante)
    y_nino = pred["nino"]["rendimiento_t_ha"]
    dif_nino = (y_nino - y_neu) / y_neu
    toneladas = (y_nino - y_neu) * area
    if abs(dif_nino) < 0.005:
        mensaje = (f"Bajo El Niño el rendimiento esperado en {municipio} prácticamente no cambia frente a un periodo neutro.")
    else:
        mensaje = [f"Si se mantiene El Niño, el rendimiento esperado en {municipio} sería {fmt(abs(dif_nino) * 100, 1)} % "
                   f"{'menor' if dif_nino < 0 else 'mayor'} que en un periodo neutro. Con el área sembrada de {per_area} "
                   f"({fmt(area, 0)} ha), equivale a unas ",
                   html.Strong(f"{fmt(abs(toneladas), 0)} t {'menos' if toneladas < 0 else 'más'}"),
                   f" de {etiqueta_cult.lower()}."]

    # ---- Indicadores de contexto (observados)
    h = datos.historia(mpio, variante)
    nat = datos.mediana_nacional(variante)
    ult = h.iloc[-1]
    obs_nino, obs_resto = h[h["fase"] == "El Niño"], h[h["fase"] != "El Niño"]
    if len(obs_nino) and len(obs_resto):
        dif_obs = obs_nino["rendimiento"].mean() / obs_resto["rendimiento"].mean() - 1
        val_obs, pie_obs = pct(dif_obs), f"{' y '.join(obs_nino['periodo'])} frente al resto"
        color_obs = COLORES["nino"] if dif_obs < -0.0005 else COLORES["tinta"]
    else:
        val_obs, color_obs = "Sin dato", COLORES["tinta"]
        pie_obs = "Ningún año completo en El Niño" if cultivo == "cana" else "Sin periodos de El Niño reportados"
    kpis = [
        html.Div([html.Div("Mediana histórica del municipio", className="k-lbl"),
                  html.Div([fmt(h["rendimiento"].median(), d), html.Small(" t/ha")], className="k-val"),
                  html.Div(f"{h['periodo'].iloc[0]}–{ult['periodo']} · {len(h)} periodos", className="k-foot")], className="panel kpi"),
        html.Div([html.Div("Último periodo observado", className="k-lbl"),
                  html.Div([fmt(ult["rendimiento"], d), html.Small(" t/ha")], className="k-val"),
                  html.Div(f"{ult['periodo']}, fase {ult['fase'].lower()}", className="k-foot")], className="panel kpi"),
        html.Div([html.Div("Mediana nacional de la variante", className="k-lbl"),
                  html.Div([fmt(nat, d), html.Small(" t/ha")], className="k-val"),
                  html.Div("EVA 2019–2025, todos los municipios", className="k-foot")], className="panel kpi"),
        html.Div([html.Div("Diferencia observada en El Niño", className="k-lbl"),
                  html.Div(val_obs, className="k-val", style={"color": color_obs}),
                  html.Div(pie_obs, className="k-foot")], className="panel kpi"),
    ]

    # ---- Variantes del cultivo
    vs_local = datos.variantes_municipio(mpio, cultivo)
    if len(vs_local) > 1:
        sub_var = "Rendimiento esperado de cada variante reportada en el municipio, en los tres escenarios."
        candidatas = vs_local
    else:
        sub_var = "El municipio solo reporta esta variante; las demás se muestran con su mediana nacional como referencia."
        candidatas = [v for v in VARIANTES if VARIANTES[v]["cultivo"] == cultivo]
    filas = []
    for v in candidatas:
        if v in vs_local:
            pv = pred if v == variante else cliente_api.predecir_escenarios(estado_api, mpio, municipio, cultivo, v, periodo)[0]
            filas.append({"v": v, "local": True, "pred": {e: pv[e]["rendimiento_t_ha"] for e in ESC}})
        else:
            m = datos.mediana_nacional(v)
            filas.append({"v": v, "local": False, "pred": {e: m for e in ESC}})

    # ---- Ranking departamental de sensibilidad
    filas_rank = []
    for cod, nombre in datos.municipios_con_variante(depto, variante):
        pm = pred if cod == mpio else cliente_api.predecir_escenarios(estado_api, cod, nombre, cultivo, variante, periodo)[0]
        filas_rank.append((cod, nombre, pm["nino"]["rendimiento_t_ha"] / pm["neutro"]["rendimiento_t_ha"] - 1))
    filas_rank.sort(key=lambda r: r[2])
    max_abs = max(abs(r[2]) for r in filas_rank) or 1
    visibles = filas_rank[:12]
    if mpio not in [r[0] for r in visibles]:
        visibles += [r for r in filas_rank if r[0] == mpio]
    items = [html.Li([html.Span(nombre),
                      html.Span(html.Span(style={"width": f"{abs(dif) / max_abs * 100:.0f}%",
                                                 "background": COLORES['nino'] if dif < 0 else COLORES['nina']}), className="bar"),
                      html.Span(pct(dif), className="pct", style={"color": COLORES['nino'] if dif < 0 else COLORES['nina']})],
                     className="sel" if cod == mpio else "") for cod, nombre, dif in visibles]
    if len(filas_rank) > len(visibles):
        items.append(html.Li(f"… y {len(filas_rank) - len(visibles)} municipios más con menor sensibilidad.", className="more"))
    sub_rank = (f"Cambio del rendimiento esperado bajo El Niño frente al neutro: {txt_cultivo.lower()}, {depto}, periodo {periodo}. "
                f"{len(filas_rank)} municipios reportan esta variante.")

    return (contexto, peticion, tarjetas, fig_rangos(pred, d), mensaje, kpis, fig_historia(h, nat, d),
            sub_var, fig_variantes(filas, variante, d), sub_rank, items)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PUERTO", "8050")), debug=False)
