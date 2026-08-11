import streamlit as st
import pandas as pd
import numpy as np
import json, os, struct, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import plotly.express as px
import plotly.graph_objects as go
from matplotlib import cm
from matplotlib.colors import Normalize, to_hex

try:
    from matplotlib import colormaps as _m
    CMAP = _m['Reds']
except Exception:
    CMAP = cm.get_cmap('Reds')

st.set_page_config(
    page_title='Observatorio Sismo Colombia 2026',
    page_icon='🌋', layout='wide')
D = 'data'

if os.path.exists('style.css'):
    with open('style.css', encoding='utf-8') as f:
        st.markdown('<style>' + f.read() + '</style>',
                    unsafe_allow_html=True)

# ========== CARGA DEFENSIVA ==========
def csv_(n):
    p = os.path.join(D, n)
    if not os.path.exists(p):
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except Exception:
        return pd.DataFrame()

def geo_(n):
    p = os.path.join(D, n)
    if not os.path.exists(p):
        return {'type': 'FeatureCollection', 'features': []}
    try:
        g = json.load(open(p, encoding='utf-8'))
        g['features'] = [
            f for f in g.get('features', [])
            if 'coordinates' in f.get('geometry', {})
        ]
        return g
    except Exception:
        return {'type': 'FeatureCollection', 'features': []}

# ========== BOUNDS ==========
bp = os.path.join(D, 'bounds.json')
if os.path.exists(bp):
    W, S, E, N = json.load(open(bp))['bounds']
else:
    W, S, E, N = -79.3, 1.8, -73.1, 7.9
BFLAT = [W, S, E, N]

def bounds_png(png, pngw):
    try:
        if not os.path.exists(png): return None
        if not os.path.exists(pngw): return None
        with open(png, 'rb') as f:
            head = f.read(33)
        w, h = struct.unpack('>II', head[16:24])
        with open(pngw) as f:
            v = [float(x) for x in f.read().split()]
        a, d, b, e, c, ff = v
        left = c - a / 2
        top = ff - e / 2
        right = left + a * w
        bottom = top + e * h
        if bottom >= top or left >= right:
            return None
        return [left, bottom, right, top]
    except Exception:
        return None

BINT = bounds_png(
    os.path.join(D, 'intensity_overlay.png'),
    os.path.join(D, 'intensity_overlay.pngw'))
if BINT is None:
    BINT = BFLAT

EPI = [4.903, -76.189]

d_exp = csv_('exposicion_deptos_MMI6.csv')
d_mun = csv_('exposicion_municipios_MMI6.csv')
d_con = csv_('construido_deptos_MMI6.csv')
d_sec = csv_('secundarias_deptos.csv')
d_ciu = csv_('ciudades_imt.csv')
d_est = csv_('estaciones.csv')
dep_gj = geo_('deptos_colombia.geojson')
rep = geo_('replicas.geojson')
sint = rep.get('metadata', {}).get('sintetico', False)

try:
    import geopandas as gpd
    g_dep = gpd.GeoDataFrame.from_features(dep_gj['features'])
except Exception:
    g_dep = None

AUTOR = ('Ensayo desarrollado por '
         '<b>Rafael Leonardo Ruiz Díaz</b> · '
         'un aporte para entender el sismo')

MMI = [
    ('IV', '#67a3ff', 'Moderado', 'Vibración como el paso de un camión.'),
    ('V', '#2ee6a8', 'Fuerte', 'Despierta a dormidos; caen objetos.'),
    ('VI', '#f9f759', 'Fuerte+', 'Grietas en muros; daño leve.'),
    ('VII', '#fcb448', 'Muy fuerte', 'Daño moderado en edificaciones.'),
    ('VIII', '#fb8b2c', 'Severo', 'Daño considerable; pánico.'),
    ('IX', '#e31a1c', 'Violento', 'Colapsos parciales y totales.'),
]

# ========== HELPERS ==========
def fmt(x):
    return f'{x:,.0f}'

def suma(df, col):
    if df.empty or col not in df:
        return 0.0
    return float(df[col].sum())

def lectura(txt):
    st.markdown('<div class="lectura">' + txt + '</div>',
                unsafe_allow_html=True)

def chart_cfg(fig):
    fig.update_layout(
        template='plotly_white',
        font=dict(family='Inter', size=12, color='#12263f'),
        margin=dict(l=20, r=20, t=50, b=20))

def mapa_estatico(titulo, capa=None, bb=None,
                  coro=None, items=None, nota=None,
                  puntos=None):
    fig, ax = plt.subplots(figsize=(9.5, 9.5), dpi=150)
    ax.set_facecolor('#eef2f7')

    if g_dep is not None:
        if coro is None:
            g_dep.boundary.plot(ax=ax, color='#93a1b5', linewidth=0.7)
        else:
            g_dep.plot(column=coro, cmap='Reds', ax=ax,
                       edgecolor='#8895a8', linewidth=0.7)

    if capa:
        p = os.path.join(D, capa)
        if os.path.exists(p):
            img = plt.imread(p)
            b = bb or BFLAT
            ax.imshow(img, extent=(b[0], b[2], b[1], b[3]),
                      alpha=0.9, zorder=3)
        else:
            st.caption('⚠️ Falta: ' + capa)

    if puntos:
        for lon, lat, r in puntos:
            ax.plot(lon, lat, 'o', color='#d10000',
                    markersize=r, markeredgecolor='white',
                    markeredgewidth=0.6, alpha=0.7, zorder=4)

    ax.plot(EPI[1], EPI[0], '*', color='#d10000',
            markersize=16, markeredgecolor='white',
            markeredgewidth=1.2, zorder=6)

    if items:
        hs = [Patch(facecolor=c, edgecolor='#444', label=t)
              for c, t in items]
        labels = [t for c, t in items]
        lg = ax.legend(handles=hs, labels=labels,
                       loc='lower left', fontsize=9,
                       title=titulo, framealpha=0.97)
        lg.get_frame().set_facecolor('white')
        lg.get_frame().set_edgecolor('#8895a8')
        lg.get_title().set_color('#0b1f3a')
        for tx in lg.get_texts():
            tx.set_color('#12263f')

    if nota:
        ax.text(0.0, -0.015, nota,
                transform=ax.transAxes, fontsize=8,
                color='#46587a')
    ax.set_xlim(W - 0.4, E + 0.4)
    ax.set_ylim(S - 0.4, N + 0.4)
    ax.set_aspect(1.0)
    ax.set_xticks([])
    ax.set_yticks([])
    st.pyplot(fig)
    plt.close(fig)

# ========== SECCIONES ==========
def sec_inicio():
    st.markdown(
        '<div class="hero">'
        '<h1 style="color:#ffffff !important;">'
        'Terremoto de Colombia M7.4</h1>'
        '<p>Observatorio ciudadano de exposición '
        'y riesgo · 10 de agosto de 2026</p>'
        '<span class="badge">USGS ShakeMap</span>'
        '<span class="badge">WorldPop</span>'
        '<span class="badge">Sentinel-1</span>'
        '<div class="autor">' + AUTOR + '</div>'
        '</div>', unsafe_allow_html=True)

    lectura(
        '<b>¿Qué es este sitio?</b> Un panel '
        'interactivo que traduce los datos técnicos '
        'del sismo en información comprensible: '
        'cuántas personas sintieron el temblor, qué '
        'zonas pueden sufrir deslizamientos y qué '
        'ciudades deben priorizar revisiones.')

    tot = suma(d_exp, 'pob_MMI6plus')
    km2 = suma(d_con, 'km2_const_MMI6')
    n_dep = 0 if d_exp.empty else int((d_exp.pob_MMI6plus > 0).sum())
    n_mun = 0 if d_mun.empty else int((d_mun.pob_MMI6plus > 0).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Personas con sacudida fuerte', fmt(tot))
    c2.metric('Departamentos afectados', n_dep)
    c3.metric('Municipios afectados', n_mun)
    c4.metric('km² urbanos expuestos', fmt(km2))
    st.markdown('---')

    mapa_estatico(
        'Intensidad (MMI)',
        capa='intensity_overlay.png', bb=BINT,
        items=[(x[1], x[0] + ' ' + x[2]) for x in MMI],
        nota='Render oficial USGS ShakeMap · estrella = epicentro')

    lectura(
        '<b>Cómo leer el mapa:</b> los colores '
        'cálidos (amarillo→rojo) indican sacudida más '
        'fuerte; la estrella es el epicentro.')


def sec_sismo():
    st.title('🌍 El sismo en contexto')
    lectura(
        '<b>Resumen:</b> un sismo de magnitud '
        '7.4 con hipocentro profundo (~107 km) bajo '
        'el Chocó. Al ser profundo, la sacudida se '
        'sintió en un área muy amplia, pero el daño '
        'extremo quedó más localizado que en un sismo '
        'superficial.')

    a, b = st.columns(2)
    with a:
        st.metric('Magnitud (Mw)', '7.4')
        st.metric('Profundidad', '~107 km')
    with b:
        st.metric('Epicentro', '4.90°N, 76.19°O')
        st.metric('Fecha', '10-ago-2026')
    st.markdown('---')
    st.subheader('Réplicas')

    if sint:
        st.warning('Catálogo ilustrativo '
                   '(Omori–GR): la API del USGS aún no '
                   'publica réplicas.')

    feats = rep.get('features', [])
    if feats:
        mags = [f['properties']['mag'] for f in feats]
        t_h = [f['properties'].get('time_h', 0) for f in feats]
        pts = [(f['geometry']['coordinates'][0],
                f['geometry']['coordinates'][1],
                1.5 + f['properties']['mag'] * 1.2)
               for f in feats]
        mapa_estatico(
            'Réplicas', puntos=pts,
            items=[('#d10000', 'Réplicas (tamaño = magnitud)')],
            nota='Catálogo Omori–GR')
        c1, c2 = st.columns(2)
        with c1:
            fig = px.scatter(x=t_h, y=mags,
                             labels={'x': 'Horas desde el sismo',
                                     'y': 'Magnitud'},
                             title='Réplicas en el tiempo')
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')
        with c2:
            fig = px.histogram(x=mags, nbins=20,
                               labels={'x': 'Magnitud'},
                               title='Frecuencia–magnitud')
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')

    with st.expander('¿Qué es una réplica y por qué decaen con el tiempo?'):
        st.write('Tras el sismo principal, la corteza se reajusta '
                 'generando sismos menores. La ley de Omori describe '
                 'el decaimiento de su frecuencia, y la de '
                 'Gutenberg–Richter por qué hay muchas pequeñas y '
                 'pocas grandes.')


def sec_comparativa():
    st.title('🆚 Dos sismos, dos historias')
    lectura(
        '<b>Más allá de la magnitud:</b> por '
        'qué sismos de tamaño similar pueden generar '
        'impactos radicalmente diferentes. De la roca '
        'a la ciudad.')

    a, b = st.columns(2)
    with a:
        st.markdown(
            '<div class="card card-col">'
            '<h3>🏔️ Caso Colombia · 10-ago-2026</h3>'
            '<b>Mw 7.4 · Profundidad ~107 km</b>'
            '<ul class="mini">'
            '<li><b>Ruptura profunda:</b> mayor '
            'recorrido de las ondas hasta la superficie.</li>'
            '<li><b>Mayor dispersión:</b> las ondas '
            'se atenúan significativamente antes de llegar.</li>'
            '<li><b>Área afectada:</b> movimiento perceptible '
            'en una región muy extensa, con menor violencia '
            'puntual.</li></ul></div>',
            unsafe_allow_html=True)
    with b:
        st.markdown(
            '<div class="card card-ven">'
            '<h3>🏙️ Caso Venezuela · 4-jun-2026</h3>'
            '<b>Doblete Mw 7.2 + 7.5 · ~10–20 km</b>'
            '<ul class="mini">'
            '<li><b>Ruptura somera:</b> muy próxima a zonas urbanas.</li>'
            '<li><b>Menor atenuación:</b> las ondas golpean con mayor energía.</li>'
            '<li><b>Doblete sísmico:</b> dos demandas sucesivas sobre '
            'estructuras posiblemente degradadas por el primer evento.</li>'
            '</ul></div>', unsafe_allow_html=True)
    st.markdown('---')

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(
            x=['Colombia', 'Venezuela'], y=[107, 15],
            labels={'y': 'Profundidad (km)', 'x': ''},
            title='Profundidad del hipocentro',
            color=['Colombia', 'Venezuela'],
            color_discrete_map={'Colombia': '#2563eb',
                                'Venezuela': '#ea580c'})
        chart_cfg(fig)
        st.plotly_chart(fig, width='stretch')
    with c2:
        ds = list(range(10, 301, 10))
        som = [120 * math.exp(-d / 90) + 4 for d in ds]
        prof = [70 * math.exp(-d / 160) + 3 for d in ds]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ds, y=som, mode='lines',
                                 name='Somero (VEN)',
                                 line={'color': '#ea580c', 'width': 3}))
        fig.add_trace(go.Scatter(x=ds, y=prof, mode='lines',
                                 name='Profundo (COL)',
                                 line={'color': '#2563eb', 'width': 3}))
        fig.update_layout(
            title='Atenuación con la distancia (esquemático)',
            xaxis_title='Distancia a la ruptura (km)',
            yaxis_title='Sacudida relativa')
        chart_cfg(fig)
        st.plotly_chart(fig, width='stretch')
    st.caption('Gráfico esquemático didáctico: un sismo somero '
               'concentra daño extremo cerca de la falla; uno profundo '
               'reparte sacudida moderada en un área amplia.')

    st.subheader('El suelo transforma la sacudida')
    a, b = st.columns(2)
    with a:
        st.markdown(
            '<div class="card card-suelo">'
            '<h3>🏜️ Cuenca y topografía</h3>'
            '<ul class="mini">'
            '<li>El contraste de rigidez de los estratos refleja, '
            'refracta y filtra las ondas.</li>'
            '<li><b>Depósitos blandos:</b> posible amplificación y '
            'mayor duración.</li>'
            '<li><b>Cuencas:</b> reflejo y atrapamiento de ondas.</li>'
            '<li><b>Relieves:</b> concentración o dispersión según su geometría.</li>'
            '</ul></div>', unsafe_allow_html=True)
    with b:
        st.markdown(
            '<div class="card card-suelo">'
            '<h3>💦 Licuación de suelos</h3>'
            '<ul class="mini">'
            '<li>Pérdida súbita de resistencia del terreno.</li>'
            '<li>Requiere: suelo granular suelto + saturación de agua '
            '+ demanda cíclica fuerte.</li>'
            '<li>Las estructuras pueden hundirse o inclinarse por '
            'pérdida de soporte.</li></ul></div>',
            unsafe_allow_html=True)

    st.subheader('Cada estructura "escucha" un sismo diferente')
    a, b, c = st.columns(3)
    with a:
        st.markdown(
            '<div class="card card-col"><h3>🏠 Bajas (1–3 pisos)</h3>'
            '<p class="mini">Responden con mayor fuerza a ondas de '
            'periodo corto (alta frecuencia, ~0.3 s).</p></div>',
            unsafe_allow_html=True)
    with b:
        st.markdown(
            '<div class="card card-col"><h3>🏢 Medianas</h3>'
            '<p class="mini">Más sensibles a ondas de periodo '
            'intermedio (~1.0 s).</p></div>',
            unsafe_allow_html=True)
    with c:
        st.markdown(
            '<div class="card card-col"><h3>🏙️ Altas</h3>'
            '<p class="mini">Entran en resonancia con ondas de '
            'periodo largo (baja frecuencia, ~3.0 s).</p></div>',
            unsafe_allow_html=True)

    lectura(
        '<b>Compatibilidad espectral:</b> si el suelo amplifica '
        'periodos cercanos al periodo natural de una estructura, '
        'su respuesta y el daño pueden aumentar dramáticamente. '
        '<b>Misma magnitud ≠ misma demanda</b> para todos los edificios.')

    st.markdown(
        '<div class="risk-banner">Riesgo Sísmico = '
        'Amenaza × Exposición × Vulnerabilidad</div>',
        unsafe_allow_html=True)

    st.subheader('El desastre depende de lo construido')
    a, b = st.columns(2)
    with a:
        st.markdown(
            '<div class="card card-ven">'
            '<h3>🏗️ Norma moderna ≠ desempeño</h3>'
            '<p class="mini">Tener un código sísmico avanzado '
            '(NSR-10, COVENIN) es solo el primer paso: su efecto '
            'real depende de la correcta aplicación.</p></div>',
            unsafe_allow_html=True)
    with b:
        st.markdown(
            '<div class="card card-ven">'
            '<h3>⚠️ Factores de vulnerabilidad</h3>'
            '<ul class="mini">'
            '<li>Edad y sistema estructural.</li>'
            '<li>Calidad de materiales y construcción.</li>'
            '<li>Detallado dúctil e irregularidades.</li>'
            '<li>Supervisión de obra y mantenimiento.</li>'
            '</ul></div>', unsafe_allow_html=True)
    st.caption('Diseño e investigación original: Rafael Leonardo Ruiz Díaz.')


def sec_intensidad():
    st.title('🎯 ¿Con qué fuerza se sintió?')
    lectura(
        '<b>Idea clave:</b> la <b>magnitud</b> es la energía liberada '
        '(una sola cifra); la <b>intensidad (MMI)</b> es cuánto se '
        'sintió en cada lugar (varía con la distancia).')

    st.subheader('Escala de Mercalli Modificada')
    cols = st.columns(len(MMI))
    for i, (num, col, nom, desc) in enumerate(MMI):
        with cols[i]:
            st.markdown(
                '<div class="mmi-chip" style="background:' + col + '">'
                '<span class="num">' + num + '</span>'
                '<b>' + nom + '</b><br>' + desc + '</div>',
                unsafe_allow_html=True)
    st.markdown('---')
    mapa_estatico(
        'Intensidad (MMI)',
        capa='intensity_overlay.png', bb=BINT,
        items=[(x[1], x[0] + ' ' + x[2]) for x in MMI],
        nota='Render oficial USGS ShakeMap, alineado con su world file (.pngw)')

    with st.expander('¿Cómo se calculó este mapa?'):
        st.write('El USGS combina registros de acelerógrafos, reportes '
                 'ciudadanos y modelos de atenuación. Mostramos el '
                 'render oficial del ShakeMap.')


def sec_poblacion():
    st.title('👥 ¿Cuántas personas fueron expuestas?')
    lectura(
        '<b>Idea clave:</b> cruzamos el mapa de intensidad con el '
        'mapa de población (WorldPop, 100 m) para estimar cuántas '
        'personas viven en zonas con cada nivel de sacudida.')

    tot = suma(d_exp, 'pob_MMI6plus')
    st.metric('Población con MMI ≥ 6', fmt(tot))

    coro = None
    if g_dep is not None and not d_exp.empty:
        vals = dict(zip(d_exp.ADM1_NAME, d_exp.pob_MMI6plus))
        coro = [vals.get(n, 0) for n in g_dep.ADM1_NAME]

    mapa_estatico(
        'Población expuesta', coro=coro,
        items=[(to_hex(CMAP(0.15)), 'Baja'),
               (to_hex(CMAP(0.5)), 'Media'),
               (to_hex(CMAP(0.9)), 'Alta')],
        nota='Coropleta: personas en MMI ≥ 6 por departamento')

    a, b = st.columns(2)
    with a:
        if not d_exp.empty:
            top = d_exp.sort_values('pob_MMI6plus').tail(10)
            fig = px.bar(top, x='pob_MMI6plus', y='ADM1_NAME',
                         orientation='h', color='pob_MMI6plus',
                         color_continuous_scale='Reds',
                         title='Departamentos más expuestos')
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')
    with b:
        if not d_mun.empty:
            top = d_mun.sort_values('pob_MMI6plus').tail(15)
            fig = px.bar(top, x='pob_MMI6plus', y='ADM2_NAME',
                         orientation='h',
                         title='Municipios más expuestos')
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')

    with st.expander('¿Qué significa "expuesta"?'):
        st.write('No implica daño: significa vivir en una zona donde '
                 'la sacudida superó MMI 6. Es una medida de cuántas '
                 'personas deben considerarse en revisiones y prevención.')


def sec_edificaciones():
    st.title('🏗️ Edificaciones e ingeniería')
    lectura(
        '<b>Idea clave:</b> distintas estructuras resuenan con '
        'distintos períodos. Las <b>PSA</b> miden la sacudida en cada '
        'período: 0.3 s casas bajas, 1.0 s edificios medios, 3.0 s '
        'puentes y torres.')

    km2 = suma(d_con, 'km2_const_MMI6')
    st.metric('km² urbanos en MMI ≥ 6', fmt(km2))

    if not d_con.empty:
        fig = px.bar(d_con.sort_values('km2_const_MMI6').tail(10),
                     x='km2_const_MMI6', y='ADM1_NAME',
                     orientation='h',
                     title='Huella urbana expuesta por departamento')
        chart_cfg(fig)
        st.plotly_chart(fig, width='stretch')
    st.markdown('---')

    st.subheader('Espectros de respuesta por ciudad')
    if not d_ciu.empty:
        opts = d_ciu.ciudad.tolist()
        defs = [o for o in ['Cali', 'Pereira', 'Manizales', 'Bogota']
                if o in opts]
        sel = st.multiselect('Ciudades', opts, default=defs)
        TS = [0.03, 0.3, 0.6, 1.0, 3.0]
        cols = ['pga', 'psa03', 'psa06', 'psa10', 'psa30']
        fig = go.Figure()
        for c in sel:
            rr = d_ciu[d_ciu.ciudad == c]
            if rr.empty: continue
            r = rr.iloc[0]
            fig.add_trace(go.Scatter(x=TS, y=[r[k] for k in cols],
                                     mode='lines+markers', name=c))
        fig.update_layout(xaxis_type='log', yaxis_type='log',
                          xaxis_title='Período (s)',
                          yaxis_title='Sa (%g)',
                          title='Espectros de respuesta')
        chart_cfg(fig)
        st.plotly_chart(fig, width='stretch')
        st.dataframe(d_ciu.sort_values('psa03', ascending=False),
                     width='stretch')

    with st.expander('¿Cómo leer un espectro?'):
        st.write('Cada línea es una ciudad. Curva alta en 0.3 s → '
                 'sufren más las casas de 1–3 pisos; alta en 1.0 s → '
                 'edificios medios. Compara ciudades para priorizar el '
                 'tipo de revisión estructural.')


def sec_secundarias():
    st.title('⛰️ Deslizamientos y licuefacción')
    lectura(
        '<b>Idea clave:</b> el sismo puede desencadenar otros '
        'peligros: <b>deslizamientos</b> en laderas empinadas y '
        '<b>licuefacción</b> en valles planos y húmedos. Los '
        'modelamos con PGA, pendiente (SRTM) y humedad.')

    capa = st.radio('Capa', ['desliz.png', 'liq.png', 'sar.png'],
                    horizontal=True,
                    format_func=lambda x: {
                        'desliz.png': '🟠 Deslizamientos',
                        'liq.png': '🔵 Licuefacción',
                        'sar.png': '🛰️ Cambio SAR'}[x])

    if capa == 'desliz.png':
        items = [('#ffffb2', 'Baja'), ('#fd8d3c', 'Media'),
                 ('#bd0026', 'Alta')]
        nota = ('Susceptibilidad = PGA × pendiente, '
                'calibrada en zona sacudida')
    elif capa == 'liq.png':
        items = [('#deebf7', 'Baja'), ('#6baed6', 'Media'),
                 ('#08519c', 'Alta')]
        nota = ('Licuefacción: valles planos y húmedos '
                'con sacudida fuerte')
    else:
        items = [('#000000', 'Sin cambio'), ('#ff4500', 'Cambio ≥ 2.5 dB')]
        nota = 'Sentinel-1: |log-ratio VH| pre/post'

    mapa_estatico('Amenaza secundaria', capa=capa,
                  items=items, nota=nota)

    if not d_sec.empty:
        a, b = st.columns(2)
        with a:
            fig = px.bar(d_sec.sort_values('km2_desliz').tail(10),
                         x='km2_desliz', y='ADM1_NAME',
                         orientation='h',
                         title='km² susceptibles a deslizamientos')
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')
        with b:
            fig = px.bar(d_sec.sort_values('km2_liq').tail(10),
                         x='km2_liq', y='ADM1_NAME',
                         orientation='h',
                         title='km² susceptibles a licuefacción')
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')

    with st.expander('¿Qué es la licuefacción?'):
        st.write('En suelos saturados, la sacudida hace que el suelo '
                 'pierda resistencia y se comporte como un líquido, '
                 'hundiendo o inclinando estructuras. Es típica de '
                 'valles aluviales.')


def sec_validacion():
    st.title('✅ Validación del modelo')
    lectura(
        '<b>Idea clave:</b> comparamos el PGA modelado por el USGS '
        'con el PGA registrado por estaciones reales. Si los puntos '
        'se acercan a la línea 1:1, el modelo es confiable.')

    if d_est.empty:
        st.info('El catálogo USGS no publica PGA por estación para '
                'este evento aún.')
        mapa_estatico('Intensidad (MMI)',
                      capa='intensity_overlay.png', bb=BINT,
                      items=[(x[1], x[0]) for x in MMI])
    else:
        a, b = st.columns(2)
        with a:
            fig = px.scatter(d_est, x='pga_mod', y='pga_obs',
                             log_x=True, log_y=True,
                             labels={'pga_mod': 'PGA modelado (%g)',
                                     'pga_obs': 'PGA observado (%g)'},
                             title='Observado vs modelado')
            mx = float(max(d_est.pga_obs.max(), d_est.pga_mod.max()))
            mn = max(0.01, float(min(d_est.pga_obs.min(),
                                     d_est.pga_mod.min())))
            fig.add_trace(go.Scatter(x=[mn, mx], y=[mn, mx],
                                     mode='lines', name='1:1',
                                     line={'dash': 'dash'}))
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')
        with b:
            fig = px.scatter(d_est, x='dist_km', y='pga_obs',
                             log_y=True,
                             labels={'dist_km': 'Distancia epicentral (km)',
                                     'pga_obs': 'PGA observado (%g)'},
                             title='Atenuación con distancia')
            fig.add_trace(go.Scatter(x=d_est.dist_km,
                                     y=d_est.pga_mod,
                                     mode='markers', name='modelado',
                                     marker={'symbol': 'x'}))
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')


def sec_aprende():
    st.title('📚 Glosario y conceptos')
    lectura('Esta sección explica, sin tecnicismos, cada término '
            'usado en el observatorio.')
    terms = [
        ('Magnitud (Mw)',
         'Energía total liberada. Una sola cifra por sismo. '
         'Cada unidad = ~32× más energía.'),
        ('Intensidad (MMI)',
         'Cuánto se sintió en un lugar. Va de I a X+ y '
         'disminuye con la distancia.'),
        ('PGA',
         'Aceleración máxima del suelo (% de la gravedad). '
         'Mide la "fuerza" del temblor.'),
        ('PSA',
         'Aceleración espectral en un período. Indica qué tipo '
         'de edificio resuena más.'),
        ('Exposición',
         'Personas o infraestructura en zonas sacudidas. '
         'No implica daño.'),
        ('Susceptibilidad',
         'Probabilidad relativa de que una ladera falle por el sismo.'),
        ('Licuefacción',
         'Pérdida de resistencia del suelo saturado por la sacudida.'),
        ('Doblete sísmico',
         'Dos sismos grandes sucesivos: el segundo golpea '
         'estructuras ya degradadas por el primero.'),
        ('Compatibilidad espectral',
         'Cuando el suelo amplifica periodos cercanos al periodo '
         'natural de una estructura, el daño aumenta.'),
    ]
    for t, d in terms:
        with st.expander(t):
            st.write(d)


def sec_metodologia():
    st.title('🔬 Metodología, fuentes y límites')
    texto = (
        "**Autor:** Rafael Leonardo Ruiz Díaz. Ensayo de "
        "divulgación para entender el sismo.\n\n"
        "**Fuentes:** USGS ShakeMap us6000tjl2 · WorldPop 2020 · "
        "ESA WorldCover · VIIRS · SRTM · CHIRPS · Sentinel-1 · "
        "FAO GAUL.\n\n"
        "**Método:** exposición = ShakeMap MMI × población a "
        "escala nativa (100 m); deslizamientos = PGA × pendiente; "
        "licuefacción = PGA × (1−pendiente) × humedad; calibrado "
        "dentro de la zona sacudida (MMI ≥ 5).\n\n"
        "**Comparativa regional:** el análisis Colombia–Venezuela "
        "sigue el marco Amenaza × Exposición × Vulnerabilidad.\n\n"
        "**Limitaciones:** productos modelados; el raster MMI "
        "cubre el núcleo de sacudida; réplicas simuladas si la "
        "API no publica.")
    st.markdown(texto)
    st.markdown('---')

    st.subheader('Estado de los archivos de datos')
    rows = []
    if os.path.exists(D):
        for f in sorted(os.listdir(D)):
            rows.append({
                'archivo': f,
                'KB': round(os.path.getsize(os.path.join(D, f)) / 1024, 1)})
        st.dataframe(pd.DataFrame(rows), width='stretch')

    st.subheader('Descarga de datos')
    if os.path.exists(D):
        for f in sorted(os.listdir(D)):
            if f.endswith('.csv'):
                try:
                    st.download_button(
                        f, open(os.path.join(D, f), 'rb').read(),
                        file_name=f, key=f)
                except Exception:
                    pass


# ========== NAVEGACIÓN ==========
st.sidebar.title('🌋 Observatorio')
st.sidebar.caption('Sismo M7.4 · Colombia')

SECCIONES = [
    '🏠 Inicio',
    '🌍 El sismo',
    '🆚 Colombia vs Venezuela',
    '🎯 Intensidad (MMI)',
    '👥 Población expuesta',
    '🏗️ Edificaciones',
    '⛰️ Amenazas secundarias',
    '✅ Validación',
    '📚 Aprende',
    '🔬 Metodología y datos',
]
op = st.sidebar.radio('Secciones', SECCIONES)
st.sidebar.markdown('---')
st.sidebar.caption(
    'Ensayo: **Rafael Leonardo Ruiz Díaz** · '
    'un aporte para entender el sismo')

RUTAS = {
    '🏠 Inicio': sec_inicio,
    '🌍 El sismo': sec_sismo,
    '🆚 Colombia vs Venezuela': sec_comparativa,
    '🎯 Intensidad (MMI)': sec_intensidad,
    '👥 Población expuesta': sec_poblacion,
    '🏗️ Edificaciones': sec_edificaciones,
    '⛰️ Amenazas secundarias': sec_secundarias,
    '✅ Validación': sec_validacion,
    '📚 Aprende': sec_aprende,
    '🔬 Metodología y datos': sec_metodologia,
}
RUTAS[op]()