import streamlit as st
import pandas as pd
import numpy as np
import json, os, struct, math
import folium
from folium import raster_layers
from folium import Element
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium
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
    st.markdown('<style>' +
      open('style.css').read() + '</style>',
      unsafe_allow_html=True)

# ---------- carga defensiva ----------
def csv_(n):
    p = f'{D}/{n}'
    if not os.path.exists(p):
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except Exception:
        return pd.DataFrame()

def geo_(n):
    p = f'{D}/{n}'
    if not os.path.exists(p):
        return {'type': 'FeatureCollection',
                'features': []}
    try:
        g = json.load(open(p))
        g['features'] = [f for f in
          g.get('features', [])
          if 'coordinates' in f.get(
            'geometry', {})]
        return g
    except Exception:
        return {'type': 'FeatureCollection',
                'features': []}

# ---------- bounds + alineación USGS ----------
bp = f'{D}/bounds.json'
if os.path.exists(bp):
    W, S, E, N = json.load(open(bp))['bounds']
else:
    W, S, E, N = -79.3, 1.8, -73.1, 7.9
BOUNDS = [[S, W], [N, E]]

def bounds_png(png, pngw):
    try:
        if not os.path.exists(png):
            return None
        if not os.path.exists(pngw):
            return None
        with open(png, 'rb') as f:
            head = f.read(33)
        w, h = struct.unpack(
          '>II', head[16:24])
        with open(pngw) as f:
            v = [float(x) for x in
                 f.read().split()]
        a, d, b, e, c, ff = v
        left = c - a / 2
        top = ff - e / 2
        right = left + a * w
        bottom = top + e * h
        return [[bottom, left], [top, right]]
    except Exception:
        return None

BINT = bounds_png(
  f'{D}/intensity_overlay.png',
  f'{D}/intensity_overlay.pngw')
def valida_b(b):
    try:
        return (b[0][0] < b[1][0]) and \
               (b[0][1] < b[1][1])
    except Exception:
        return False

if BINT is None or not valida_b(BINT):
    BINT = BOUNDS

EPI = [4.903, -76.189]

d_exp = csv_('exposicion_deptos_MMI6.csv')
d_mun = csv_('exposicion_municipios_MMI6.csv')
d_con = csv_('construido_deptos_MMI6.csv')
d_sec = csv_('secundarias_deptos.csv')
d_ciu = csv_('ciudades_imt.csv')
d_est = csv_('estaciones.csv')
dep_gj = geo_('deptos_colombia.geojson')
rep = geo_('replicas.geojson')
sint = rep.get('metadata', {}).get(
  'sintetico', False)

def suma(df, col):
    if df.empty or col not in df:
        return 0.0
    return float(df[col].sum())

def fmt(x):
    return f'{x:,.0f}'

AUTOR = ('Ensayo desarrollado por '
  '<b>Rafael Leonardo Ruiz Díaz</b> · '
  'un aporte para entender el sismo')

MMI = [
  ('IV', '#67a3ff', 'Moderado',
   'Vibración como el paso de un camión.'),
  ('V', '#2ee6a8', 'Fuerte',
   'Despierta a dormidos; caen objetos.'),
  ('VI', '#f9f759', 'Fuerte+',
   'Grietas en muros; daño leve.'),
  ('VII', '#fcb448', 'Muy fuerte',
   'Daño moderado en edificaciones.'),
  ('VIII', '#fb8b2c', 'Severo',
   'Daño considerable; pánico.'),
  ('IX', '#e31a1c', 'Violento',
   'Colapsos parciales y totales.')]

# ---------- helpers ----------
def mapa_base(zoom=7):
    m = folium.Map(location=[4.9, -76.2],
      zoom_start=zoom)
    folium.TileLayer('cartodbpositron',
      name='Base clara').add_to(m)
    folium.TileLayer(
      tiles='https://server.arcgisonline.com/'
        'ArcGIS/rest/services/World_Imagery/'
        'MapServer/tile/{z}/{y}/{x}',
      attr='Esri', name='Satélite').add_to(m)
    folium.LayerControl().add_to(m)
    return m

def overlay(m, png, op_=0.7, bb=None):
    p = f'{D}/{png}'
    if bb is None:
        bb = BOUNDS
    if os.path.exists(p):
        raster_layers.ImageOverlay(
          p, bounds=bb,
          opacity=op_).add_to(m)

def epi(m):
    folium.Marker(EPI,
      popup='Epicentro M7.4',
      icon=folium.Icon(
        color='red', icon='star')).add_to(m)

def mostrar_mapa(m, h=520):
    try:
        st_folium(m, height=h)
    except Exception as e:
        st.error('El mapa no se pudo renderizar: '
          + str(e))

def leyenda(m, titulo, items, nota=''):
    h = ('<div style="position:fixed;'
      'bottom:24px;left:12px;z-index:999;'
      'background:rgba(255,255,255,.97);'
      'color:#12263f;padding:12px 16px;'
      'border-radius:12px;'
      'box-shadow:0 4px 16px '
      'rgba(0,0,0,.35);'
      'font-family:Inter,Arial,sans-serif;'
      'font-size:12px;line-height:1.9;'
      'min-width:160px;">'
      '<div style="font-weight:800;'
      'font-size:13px;margin-bottom:4px;'
      'color:#0b1f3a;">' + titulo + '</div>')
    for c, t in items:
        h += ('<div><i style="background:' + c +
          ';display:inline-block;width:14px;'
          'height:14px;margin-right:8px;'
          'border-radius:4px;'
          'vertical-align:-2px;'
          'box-shadow:inset 0 0 0 1px '
          'rgba(0,0,0,.25);"></i>'
          '<span style="color:#12263f;">'
          + t + '</span></div>')
    if nota:
        h += ('<div style="margin-top:6px;'
          'font-size:10px;color:#46587a;">'
          + nota + '</div>')
    h += '</div>'
    m.get_root().html.add_child(Element(h))

def lectura(txt):
    st.markdown('<div class="lectura">' +
      txt + '</div>', unsafe_allow_html=True)

def chart_cfg(fig):
    fig.update_layout(
      template='plotly_white',
      font=dict(family='Inter', size=12,
                color='#12263f'),
      margin=dict(l=20, r=20, t=50, b=20))

# ---------- navegación ----------
st.sidebar.title('🌋 Observatorio')
st.sidebar.caption('Sismo M7.4 · Colombia')
op = st.sidebar.radio('Secciones', [
  '🏠 Inicio',
  '🌍 El sismo',
  '🆚 Colombia vs Venezuela',
  '🎯 Intensidad (MMI)',
  '👥 Población expuesta',
  '🏗�?Edificaciones',
  '⛰️ Amenazas secundarias',
  '�?Validación',
  '📚 Aprende',
  '🔬 Metodología y datos'])
st.sidebar.markdown('---')
st.sidebar.caption(
  'Ensayo: **Rafael Leonardo Ruiz Díaz** · '
  'un aporte para entender el sismo')

# ============ INICIO ============
if op == '🏠 Inicio':
    st.markdown('<div class="hero">'
      '<h1 style="color:#ffffff !important;">'
      'Terremoto de Colombia M7.4</h1>'
      '<p>Observatorio ciudadano de exposición '
      'y riesgo · 10 de agosto de 2026</p>'
      '<span class="badge">USGS ShakeMap</span>'
      '<span class="badge">WorldPop</span>'
      '<span class="badge">Sentinel-1</span>'
      '<div class="autor">' + AUTOR + '</div>'
      '</div>', unsafe_allow_html=True)
    lectura('<b>¿Qué es este sitio?</b> Un panel '
      'interactivo que traduce los datos técnicos '
      'del sismo en información comprensible: '
      'cuántas personas sintieron el temblor, qué '
      'zonas pueden sufrir deslizamientos y qué '
      'ciudades deben priorizar revisiones.')
    tot = suma(d_exp, 'pob_MMI6plus')
    km2 = suma(d_con, 'km2_const_MMI6')
    n_dep = int((d_exp.pob_MMI6plus > 0).sum()) \
      if not d_exp.empty else 0
    n_mun = int((d_mun.pob_MMI6plus > 0).sum()) \
      if not d_mun.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Personas con sacudida fuerte',
              fmt(tot))
    c2.metric('Departamentos afectados', n_dep)
    c3.metric('Municipios afectados', n_mun)
    c4.metric('km² urbanos expuestos', fmt(km2))
    st.markdown('---')
    m = mapa_base()
    overlay(m, 'intensity_overlay.png', 0.85,
            BINT)
    epi(m)
    leyenda(m, 'Intensidad (MMI)',
      [(x[1], x[0]) for x in MMI],
      nota='Render oficial USGS ShakeMap')
    mostrar_mapa(m, 540)
    lectura('<b>Cómo leer el mapa:</b> los colores '
      'cálidos (amarillo→rojo) indican sacudida más '
      'fuerte. La estrella es el epicentro. Usa el '
      'control de capas (arriba a la derecha) para '
      'alternar base clara o satélite.')

# ============ EL SISMO ============
elif op == '🌍 El sismo':
    st.title('🌍 El sismo en contexto')
    lectura('<b>Resumen:</b> un sismo de magnitud '
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
        mags = [f['properties']['mag']
                for f in feats]
        t_h = [f['properties'].get('time_h', 0)
               for f in feats]
        m = mapa_base()
        for f in feats:
            co = f['geometry']['coordinates']
            mg = f['properties']['mag']
            folium.CircleMarker([co[1], co[0]],
              radius=2 + mg * 1.5,
              color='crimson', fill=True,
              fill_opacity=0.5).add_to(m)
        epi(m)
        mostrar_mapa(m, 420)
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
    with st.expander('¿Qué es una réplica y por '
      'qué decaen con el tiempo?'):
        st.write('Tras el sismo principal, la '
          'corteza se reajusta generando sismos '
          'menores. La ley de Omori describe el '
          'decaimiento de su frecuencia, y la de '
          'Gutenberg–Richter por qué hay muchas '
          'pequeñas y pocas grandes.')

# ============ COMPARATIVA ============
elif op == '🆚 Colombia vs Venezuela':
    st.title('🆚 Dos sismos, dos historias')
    lectura('<b>Más allá de la magnitud:</b> sismos '
      'de tamaño similar pueden generar impactos '
      'radicalmente diferentes. La profundidad, el '
      'suelo y lo construido deciden el desastre.')
    a, b = st.columns(2)
    with a:
        st.markdown('<div class="card card-col">'
          '<h3>🇨🇴 Colombia · 10-ago-2026</h3>'
          '<b>Mw 7.4 · Profundidad ~107 km</b>'
          '<ul class="mini">'
          '<li>Ruptura profunda: mayor recorrido de '
          'las ondas hasta la superficie.</li>'
          '<li>Mayor dispersión: las ondas se '
          'atenúan antes de llegar.</li>'
          '<li>Sacudida perceptible en una región '
          'muy extensa, con menor violencia '
          'puntual.</li></ul></div>',
          unsafe_allow_html=True)
    with b:
        st.markdown('<div class="card card-ven">'
          '<h3>🇻 Venezuela · 4-jun-2026</h3>'
          '<b>Doblete Mw 7.2 + 7.5 · ~10�?0 km</b>'
          '<ul class="mini">'
          '<li>Ruptura somera, muy próxima a zonas '
          'urbanas.</li>'
          '<li>Menor atenuación: las ondas golpean '
          'con mayor energía.</li>'
          '<li>Doblete sísmico: dos demandas '
          'sucesivas sobre estructuras ya '
          'degradadas por el primer evento.</li>'
          '</ul></div>', unsafe_allow_html=True)
    st.markdown('---')
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(
          x=['Colombia', 'Venezuela'],
          y=[107, 15],
          labels={'y': 'Profundidad (km)',
                  'x': ''},
          title='Profundidad del hipocentro',
          color=['Colombia', 'Venezuela'],
          color_discrete_map={
            'Colombia': '#2563eb',
            'Venezuela': '#ea580c'})
        chart_cfg(fig)
        st.plotly_chart(fig, width='stretch')
    with c2:
        ds = list(range(10, 301, 10))
        som = [120 * math.exp(-d / 90) + 4
               for d in ds]
        prof = [70 * math.exp(-d / 160) + 3
                for d in ds]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ds, y=som,
          mode='lines',
          name='Somero (VEN)',
          line={'color': '#ea580c', 'width': 3}))
        fig.add_trace(go.Scatter(x=ds, y=prof,
          mode='lines',
          name='Profundo (COL)',
          line={'color': '#2563eb', 'width': 3}))
        fig.update_layout(
          title='Atenuación con la distancia '
          '(esquemático)',
          xaxis_title='Distancia a la ruptura (km)',
          yaxis_title='Sacudida relativa')
        chart_cfg(fig)
        st.plotly_chart(fig, width='stretch')
    st.caption('Gráfico esquemático didáctico: un '
      'sismo somero concentra daño extremo cerca de '
      'la falla; uno profundo reparte sacudida '
      'moderada en un área amplia.')
    st.markdown('---')
    st.subheader('El suelo transforma la sacudida')
    a, b = st.columns(2)
    with a:
        st.markdown('<div class="card card-suelo">'
          '<h3>🏜�?Amplificación (cuencas)</h3>'
          '<ul class="mini">'
          '<li>Depósitos blandos: mayor amplitud y '
          'duración del movimiento.</li>'
          '<li>Cuencas: reflejo y atrapamiento de '
          'ondas.</li>'
          '<li>Relieves: concentran o dispersan '
          'según su geometría.</li></ul></div>',
          unsafe_allow_html=True)
    with b:
        st.markdown('<div class="card card-suelo">'
          '<h3>💦 Licuefacción de suelos</h3>'
          '<ul class="mini">'
          '<li>Pérdida súbita de resistencia del '
          'terreno.</li>'
          '<li>Requiere: suelo granular suelto + '
          'saturación de agua + demanda cíclica '
          'fuerte.</li>'
          '<li>Las estructuras pueden hundirse o '
          'inclinarse por pérdida de soporte.</li>'
          '</ul></div>', unsafe_allow_html=True)
    st.subheader('Cada estructura escucha un sismo '
      'diferente')
    a, b, c = st.columns(3)
    with a:
        st.markdown('<div class="card card-col">'
          '<h3>🏠 Bajas (1�? pisos)</h3>'
          '<p class="mini">Resuenan con periodos '
          'cortos (~0.3 s): alta frecuencia.</p>'
          '</div>', unsafe_allow_html=True)
    with b:
        st.markdown('<div class="card card-col">'
          '<h3>🏢 Medianas</h3>'
          '<p class="mini">Sensibles a periodos '
          'intermedios (~1.0 s).</p></div>',
          unsafe_allow_html=True)
    with c:
        st.markdown('<div class="card card-col">'
          '<h3>🏙�?Altas</h3>'
          '<p class="mini">Resuenan con periodos '
          'largos (~3.0 s): baja frecuencia.</p>'
          '</div>', unsafe_allow_html=True)
    lectura('<b>Compatibilidad espectral:</b> si el '
      'suelo amplifica periodos cercanos al periodo '
      'natural de una estructura, su respuesta y el '
      'daño pueden aumentar dramáticamente. Misma '
      'magnitud �?misma demanda para todos los '
      'edificios.')
    st.markdown('<div class="risk-banner">Riesgo '
      'Sísmico = Amenaza × Exposición × '
      'Vulnerabilidad</div>',
      unsafe_allow_html=True)
    with st.expander('Factores de vulnerabilidad y '
      'normas'):
        st.write('�?Norma moderna �?desempeño: tener '
          'un código avanzado (NSR-10, COVENIN) es '
          'solo el primer paso; importa su '
          'aplicación real.\n'
          '�?Edad y sistema estructural.\n'
          '�?Calidad de materiales y construcción.\n'
          '�?Detallado dúctil e irregularidades.\n'
          '�?Supervisión de obra y mantenimiento.')

# ============ INTENSIDAD ============
elif op == '🎯 Intensidad (MMI)':
    st.title('🎯 ¿Con qué fuerza se sintió?')
    lectura('<b>Idea clave:</b> la <b>magnitud</b> '
      'es la energía liberada (una sola cifra); la '
      '<b>intensidad (MMI)</b> es cuánto se sintió '
      'en cada lugar (varía con la distancia).')
    st.subheader('Escala de Mercalli Modificada')
    cols = st.columns(len(MMI))
    for i, (num, col, nom, desc) in enumerate(MMI):
        with cols[i]:
            st.markdown('<div class="mmi-chip" '
              'style="background:' + col + '">'
              '<span class="num">' + num + '</span>'
              '<b>' + nom + '</b><br>' + desc +
              '</div>', unsafe_allow_html=True)
    st.markdown('---')
    m = mapa_base()
    overlay(m, 'intensity_overlay.png', 0.85,
            BINT)
    epi(m)
    leyenda(m, 'MMI',
      [(x[1], x[0]) for x in MMI],
      nota='Render oficial USGS ShakeMap')
    mostrar_mapa(m, 520)
    with st.expander('¿Cómo se calculó este mapa?'):
        st.write('El USGS combina registros de '
          'acelerógrafos, reportes ciudadanos y '
          'modelos de atenuación. Mostramos el '
          'render oficial del ShakeMap.')

# ============ POBLACIÓN ============
elif op == '👥 Población expuesta':
    st.title('👥 ¿Cuántas personas fueron '
      'expuestas?')
    lectura('<b>Idea clave:</b> cruzamos el mapa de '
      'intensidad con el mapa de población '
      '(WorldPop, 100 m) para estimar cuántas '
      'personas viven en zonas con cada nivel de '
      'sacudida.')
    tot = suma(d_exp, 'pob_MMI6plus')
    st.metric('Población con MMI �?6', fmt(tot))
    m = mapa_base()
    if not d_exp.empty:
        nrm = Normalize(0,
          d_exp.pob_MMI6plus.max())
        vals = dict(zip(d_exp.ADM1_NAME,
          d_exp.pob_MMI6plus))
        def style(f):
            v = vals.get(
              f['properties']['ADM1_NAME'], 0)
            return {'fillColor': to_hex(CMAP(nrm(v))),
              'color': '#444', 'weight': 0.8,
              'fillOpacity': 0.75}
        folium.GeoJson(dep_gj,
          style_function=style,
          tooltip=folium.GeoJsonTooltip(
            ['ADM1_NAME'])).add_to(m)
    epi(m)
    mostrar_mapa(m, 520)
    a, b = st.columns(2)
    with a:
        if not d_exp.empty:
            top = d_exp.sort_values(
              'pob_MMI6plus').tail(10)
            fig = px.bar(top, x='pob_MMI6plus',
              y='ADM1_NAME', orientation='h',
              color='pob_MMI6plus',
              color_continuous_scale='Reds',
              title='Departamentos más expuestos')
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')
    with b:
        if not d_mun.empty:
            top = d_mun.sort_values(
              'pob_MMI6plus').tail(15)
            fig = px.bar(top, x='pob_MMI6plus',
              y='ADM2_NAME', orientation='h',
              title='Municipios más expuestos')
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')
    with st.expander('¿Qué significa "expuesta"?'):
        st.write('No implica daño: significa vivir '
          'en una zona donde la sacudida superó '
          'MMI 6. Es una medida de cuántas personas '
          'deben considerarse en revisiones y '
          'prevención.')

# ============ EDIFICACIONES ============
elif op == '🏗�?Edificaciones':
    st.title('🏗�?Edificaciones e ingeniería')
    lectura('<b>Idea clave:</b> distintas '
      'estructuras resuenan con distintos períodos. '
      'Las <b>PSA</b> miden la sacudida en cada '
      'período: 0.3 s casas bajas, 1.0 s edificios '
      'medios, 3.0 s puentes y torres.')
    km2 = suma(d_con, 'km2_const_MMI6')
    st.metric('km² urbanos en MMI �?6', fmt(km2))
    if not d_con.empty:
        fig = px.bar(d_con.sort_values(
          'km2_const_MMI6').tail(10),
          x='km2_const_MMI6', y='ADM1_NAME',
          orientation='h',
          title='Huella urbana expuesta por '
          'departamento')
        chart_cfg(fig)
        st.plotly_chart(fig, width='stretch')
    st.markdown('---')
    st.subheader('Espectros de respuesta por '
      'ciudad')
    if not d_ciu.empty:
        opts = d_ciu.ciudad.tolist()
        defs = [o for o in
          ['Cali', 'Pereira', 'Manizales',
           'Bogota'] if o in opts]
        sel = st.multiselect('Ciudades', opts,
          default=defs)
        TS = [0.03, 0.3, 0.6, 1.0, 3.0]
        cols = ['pga', 'psa03', 'psa06',
                'psa10', 'psa30']
        fig = go.Figure()
        for c in sel:
            rr = d_ciu[d_ciu.ciudad == c]
            if rr.empty:
                continue
            r = rr.iloc[0]
            fig.add_trace(go.Scatter(x=TS,
              y=[r[k] for k in cols],
              mode='lines+markers', name=c))
        fig.update_layout(xaxis_type='log',
          yaxis_type='log',
          xaxis_title='Período (s)',
          yaxis_title='Sa (%g)',
          title='Espectros de respuesta')
        chart_cfg(fig)
        st.plotly_chart(fig, width='stretch')
        st.dataframe(d_ciu.sort_values(
          'psa03', ascending=False),
          width='stretch')
    with st.expander('¿Cómo leer un espectro?'):
        st.write('Cada línea es una ciudad. Curva '
          'alta en 0.3 s �?sufren más las casas de '
          '1�? pisos; alta en 1.0 s �?edificios '
          'medios. Compara ciudades para priorizar '
          'el tipo de revisión estructural.')

# ============ SECUNDARIAS ============
elif op == '⛰️ Amenazas secundarias':
    st.title('⛰️ Deslizamientos y licuefacción')
    lectura('<b>Idea clave:</b> el sismo puede '
      'desencadenar otros peligros: '
      '<b>deslizamientos</b> en laderas empinadas y '
      '<b>licuefacción</b> en valles planos y '
      'húmedos. Los modelamos con PGA, pendiente '
      '(SRTM) y humedad.')
    capa = st.radio('Capa', [
      'desliz.png', 'liq.png', 'sar.png'],
      horizontal=True,
      format_func=lambda x: {
        'desliz.png': '🟠 Deslizamientos',
        'liq.png': '🔵 Licuefacción',
        'sar.png': '🛰�?Cambio SAR'}[x])
    m = mapa_base()
    overlay(m, capa, 0.75)
    epi(m)
    mostrar_mapa(m, 500)
    if not d_sec.empty:
        a, b = st.columns(2)
        with a:
            fig = px.bar(d_sec.sort_values(
              'km2_desliz').tail(10),
              x='km2_desliz', y='ADM1_NAME',
              orientation='h',
              title='km² susceptibles a '
              'deslizamientos')
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')
        with b:
            fig = px.bar(d_sec.sort_values(
              'km2_liq').tail(10),
              x='km2_liq', y='ADM1_NAME',
              orientation='h',
              title='km² susceptibles a '
              'licuefacción')
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')
    with st.expander('¿Qué es la licuefacción?'):
        st.write('En suelos saturados, la sacudida '
          'hace que el suelo pierda resistencia y se '
          'comporte como un líquido, hundiendo o '
          'inclinando estructuras. Es típica de '
          'valles aluviales.')

# ============ VALIDACIÓN ============
elif op == '�?Validación':
    st.title('�?Validación del modelo')
    lectura('<b>Idea clave:</b> comparamos el PGA '
      'modelado por el USGS con el PGA registrado '
      'por estaciones reales. Si los puntos se '
      'acercan a la línea 1:1, el modelo es '
      'confiable.')
    if d_est.empty:
        st.info('El catálogo USGS no publica PGA '
          'por estación para este evento aún.')
        m = mapa_base()
        overlay(m, 'intensity_overlay.png', 0.85,
                BINT)
        epi(m)
        mostrar_mapa(m, 500)
    else:
        a, b = st.columns(2)
        with a:
            fig = px.scatter(d_est,
              x='pga_mod', y='pga_obs',
              log_x=True, log_y=True,
              labels={'pga_mod': 'PGA modelado '
                '(%g)',
                'pga_obs': 'PGA observado (%g)'},
              title='Observado vs modelado')
            mx = float(max(d_est.pga_obs.max(),
              d_est.pga_mod.max()))
            mn = max(0.01, float(min(
              d_est.pga_obs.min(),
              d_est.pga_mod.min())))
            fig.add_trace(go.Scatter(
              x=[mn, mx], y=[mn, mx],
              mode='lines', name='1:1',
              line={'dash': 'dash'}))
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')
        with b:
            fig = px.scatter(d_est,
              x='dist_km', y='pga_obs',
              log_y=True,
              labels={'dist_km': 'Distancia '
                'epicentral (km)',
                'pga_obs': 'PGA observado (%g)'},
              title='Atenuación con distancia')
            fig.add_trace(go.Scatter(
              x=d_est.dist_km, y=d_est.pga_mod,
              mode='markers', name='modelado',
              marker={'symbol': 'x'}))
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')

# ============ APRENDE ============
elif op == '📚 Aprende':
    st.title('📚 Glosario y conceptos')
    lectura('Esta sección explica, sin tecnicismos, '
      'cada término usado en el observatorio.')
    terms = [
      ('Magnitud (Mw)', 'Energía total liberada. '
        'Una sola cifra por sismo. Cada unidad = '
        '~32× más energía.'),
      ('Intensidad (MMI)', 'Cuánto se sintió en un '
        'lugar. Va de I a X+ y disminuye con la '
        'distancia.'),
      ('PGA', 'Aceleración máxima del suelo (% de '
        'la gravedad). Mide la "fuerza" del '
        'temblor.'),
      ('PSA', 'Aceleración espectral en un período. '
        'Indica qué tipo de edificio resuena más.'),
      ('Exposición', 'Personas o infraestructura en '
        'zonas sacudidas. No implica daño.'),
      ('Susceptibilidad', 'Probabilidad relativa de '
        'que una ladera falle por el sismo.'),
      ('Licuefacción', 'Pérdida de resistencia del '
        'suelo saturado por la sacudida.'),
      ('Doblete sísmico', 'Dos sismos grandes '
        'sucesivos: el segundo golpea estructuras '
        'ya degradadas por el primero.')]
    for t, d in terms:
        with st.expander(t):
            st.write(d)

# ============ METODOLOGÍA ============
elif op == '🔬 Metodología y datos':
    st.title('🔬 Metodología, fuentes y límites')
    texto = (
        "**Autor:** Rafael Leonardo Ruiz Díaz. "
        "Ensayo de divulgación para entender el "
        "sismo.\n\n"
        "**Fuentes:** USGS ShakeMap us6000tjl2 · "
        "WorldPop 2020 · ESA WorldCover · VIIRS · "
        "SRTM · CHIRPS · Sentinel-1 · FAO GAUL.\n\n"
        "**Método:** exposición = ShakeMap MMI × "
        "población a escala nativa (100 m); "
        "deslizamientos = PGA × pendiente; "
        "licuefacción = PGA × (1−pendiente) × "
        "humedad; calibrado dentro de la zona "
        "sacudida (MMI �?5).\n\n"
        "**Comparativa regional:** el análisis "
        "Colombia–Venezuela sigue el marco "
        "conceptual Amenaza × Exposición × "
        "Vulnerabilidad.\n\n"
        "**Limitaciones:** productos modelados; el "
        "raster MMI cubre el núcleo de sacudida; "
        "réplicas simuladas si la API no publica.")
    st.markdown(texto)
    st.markdown('---')
    st.subheader('Estado de los archivos de datos')
    rows = []
    if os.path.exists(D):
        for f in sorted(os.listdir(D)):
            rows.append({'archivo': f,
              'KB': round(os.path.getsize(
                f'{D}/{f}') / 1024, 1)})
        st.dataframe(pd.DataFrame(rows),
          width='stretch')
        st.caption('Si algún PNG pesa pocos KB, '
          'puede estar vacío: repórtalo para '
          'regenerarlo.')
    st.subheader('Descarga de datos')
    if os.path.exists(D):
        for f in sorted(os.listdir(D)):
            if f.endswith('.csv'):
                try:
                    st.download_button(f,
                      open(f'{D}/{f}',
                           'rb').read(),
                      file_name=f, key=f)
                except Exception:
                    pass