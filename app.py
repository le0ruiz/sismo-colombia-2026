import streamlit as st
import pandas as pd
import numpy as np
import json, os
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

# ---------- estilo ----------
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

bp = f'{D}/bounds.json'
if os.path.exists(bp):
    W, S, E, N = json.load(open(bp))['bounds']
else:
    W, S, E, N = -79.3, 1.8, -73.1, 7.9
BOUNDS = [[S, W], [N, E]]
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

# ---------- constantes educativas ----------
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

# ---------- helpers de mapa ----------
def mapa_base(zoom=7):
    m = folium.Map(location=[4.9, -76.2],
      zoom_start=zoom, tiles=None)
    folium.TileLayer('cartodbpositron',
      name='Base').add_to(m)
    return m

def overlay(m, png, op_=0.7):
    p = f'{D}/{png}'
    if os.path.exists(p):
        raster_layers.ImageOverlay(
          p, bounds=BOUNDS,
          opacity=op_).add_to(m)

def epi(m):
    folium.Marker(EPI, popup='Epicentro M7.4',
      icon=folium.Icon(
        color='red', icon='star')).add_to(m)

def leyenda(m, titulo, items):
    h = ('<div style="position:fixed;bottom:24px;'
      'left:10px;z-index:999;background:white;'
      'padding:10px 14px;border-radius:10px;'
      'box-shadow:0 2px 10px rgba(0,0,0,.25);'
      'font-size:12px;line-height:1.8;">'
      '<b>' + titulo + '</b><br>')
    for c, t in items:
        h += ('<i style="background:' + c +
          ';display:inline-block;width:14px;'
          'height:14px;margin-right:6px;'
          'border-radius:3px;"></i>' + t + '<br>')
    h += '</div>'
    m.get_root().html.add_child(Element(h))

def lectura(txt):
    st.markdown('<div class="lectura">' +
      txt + '</div>', unsafe_allow_html=True)

def chart_cfg(fig):
    fig.update_layout(
      template='plotly_white',
      font=dict(family='Inter', size=12),
      margin=dict(l=20, r=20, t=50, b=20))

# ---------- navegación ----------
st.sidebar.title('🌋 Observatorio')
st.sidebar.caption('Sismo M7.4 · Colombia')
op = st.sidebar.radio('Secciones', [
  '🏠 Inicio',
  '🌍 El sismo',
  '🎯 Intensidad (MMI)',
  '👥 Población expuesta',
  '🏗️ Edificaciones',
  '⛰️ Amenazas secundarias',
  '📚 Aprende',
  '🔬 Metodología y datos'])

# ============ INICIO ============
if op == '🏠 Inicio':
    st.markdown('<div class="hero"><h1>'
      'Terremoto de Colombia M7.4</h1>'
      '<p>Observatorio ciudadano de exposición '
      'y riesgo · 10 de agosto de 2026</p>'
      '<span class="badge">USGS ShakeMap</span>'
      '<span class="badge">WorldPop</span>'
      '<span class="badge">Sentinel-1</span>'
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
    overlay(m, 'intensity_overlay.png')
    epi(m)
    leyenda(m, 'Intensidad (MMI)',
      [(x[1], x[0]) for x in MMI])
    st_folium(m, height=540)
    lectura('<b>Cómo leer el mapa:</b> los colores '
      'cálidos (amarillo→rojo) indican sacudida más '
      'fuerte. La estrella es el epicentro. Pasa el '
      'cursor para hacer zoom y explorar.')

# ============ EL SISMO ============
elif op == '🌍 El sismo':
    st.title('🌍 El sismo en contexto')
    lectura('<b>Resumen:</b> un sismo de magnitud '
      '7.4 con hipocentro profundo (~110 km) bajo '
      'el Chocó. Al ser profundo, la sacudida se '
      'sintió en un área muy amplia (todo el '
      'occidente), pero el daño extremo quedó '
      'más localizado que en un sismo superficial.')
    a, b = st.columns([1, 1])
    with a:
        st.metric('Magnitud (Mw)', '7.4')
        st.metric('Profundidad', '~110 km')
    with b:
        st.metric('Epicentro', '4.90°N, 76.19°O')
        st.metric('Fecha', '10-ago-2026')
    st.markdown('---')
    st.subheader('Réplicas')
    if sint:
        st.warning('Catálogo ilustrativo (Omori–GR): '
          'la API del USGS aún no publica réplicas.')
    feats = rep.get('features', [])
    if feats:
        mags = [f['properties']['mag'] for f in feats]
        t_h = [f['properties'].get('time_h', 0)
               for f in feats]
        m = mapa_base()
        for f in feats:
            co = f['geometry']['coordinates']
            mg = f['properties']['mag']
            folium.CircleMarker([co[1], co[0]],
              radius=2 + mg * 1.5, color='crimson',
              fill=True, fill_opacity=0.5).add_to(m)
        epi(m)
        st_folium(m, height=420)
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
    with st.expander('¿Qué es una réplica y por qué '
      'decaen con el tiempo?'):
        st.write('Tras el sismo principal, la corteza '
          'se reajusta generando sismos menores '
          '(réplicas). La ley de Omori describe cómo '
          'su frecuencia decae con el tiempo, y la de '
          'Gutenberg–Richter cómo hay muchas pequeñas '
          'y pocas grandes.')

# ============ INTENSIDAD ============
elif op == '🎯 Intensidad (MMI)':
    st.title('🎯 ¿Con qué fuerza se sintió?')
    lectura('<b>Idea clave:</b> la <b>magnitud</b> es '
      'la energía liberada (una sola cifra); la '
      '<b>intensidad (MMI)</b> es cuánto se sintió en '
      'cada lugar (varía con la distancia). Aquí '
      'mapeamos la intensidad.')
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
    overlay(m, 'intensity_overlay.png', 0.8)
    epi(m)
    leyenda(m, 'MMI', [(x[1], x[0]) for x in MMI])
    st_folium(m, height=520)
    with st.expander('¿Cómo se calculó este mapa?'):
        st.write('El USGS combina registros de '
          'acelerógrafos, reportes ciudadanos y '
          'modelos de atenuación para estimar la '
          'intensidad en cada punto. Nosotros lo '
          'reproducimos con el raster oficial.')

# ============ POBLACIÓN ============
elif op == '👥 Población expuesta':
    st.title('👥 ¿Cuántas personas fueron expuestas?')
    lectura('<b>Idea clave:</b> cruzamos el mapa de '
      'intensidad con el mapa de población (WorldPop, '
      '100 m). Así estimamos cuántas personas viven en '
      'zonas con cada nivel de sacudida.')
    tot = suma(d_exp, 'pob_MMI6plus')
    st.metric('Población con MMI ≥ 6', fmt(tot))
    m = mapa_base()
    if not d_exp.empty:
        nrm = Normalize(0, d_exp.pob_MMI6plus.max())
        vals = dict(zip(d_exp.ADM1_NAME,
          d_exp.pob_MMI6plus))
        def style(f):
            v = vals.get(
              f['properties']['ADM1_NAME'], 0)
            return {'fillColor': to_hex(CMAP(nrm(v))),
              'color': '#444', 'weight': 0.8,
              'fillOpacity': 0.75}
        folium.GeoJson(dep_gj, style_function=style,
          tooltip=folium.GeoJsonTooltip(
            ['ADM1_NAME'])).add_to(m)
    epi(m)
    st_folium(m, height=520)
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
        st.write('No implica daño: significa vivir en '
          'una zona donde la sacudida superó MMI 6. Es '
          'una medida de cuántas personas deben ser '
          'consideradas en revisiones y prevención.')

# ============ EDIFICACIONES ============
elif op == '🏗️ Edificaciones':
    st.title('🏗️ Edificaciones e ingeniería')
    lectura('<b>Idea clave:</b> distintas estructuras '
      'resuenan con distintos períodos de vibración. '
      'Las <b>PSA</b> (aceleraciones espectrales) miden '
      'la sacudida en cada período: 0.3 s afecta casas '
      'bajas, 1.0 s edificios medios, 3.0 s puentes y '
      'torres.')
    km2 = suma(d_con, 'km2_const_MMI6')
    st.metric('km² urbanos en MMI ≥ 6', fmt(km2))
    if not d_con.empty:
        fig = px.bar(d_con.sort_values(
          'km2_const_MMI6').tail(10),
          x='km2_const_MMI6', y='ADM1_NAME',
          orientation='h',
          title='Huella urbana expuesta por departamento')
        chart_cfg(fig)
        st.plotly_chart(fig, width='stretch')
    st.markdown('---')
    st.subheader('Espectros de respuesta por ciudad')
    if not d_ciu.empty:
        opts = d_ciu.ciudad.tolist()
        defs = [o for o in
          ['Cali', 'Pereira', 'Manizales', 'Bogota']
          if o in opts]
        sel = st.multiselect('Ciudades', opts,
          default=defs)
        TS = [0.03, 0.3, 0.6, 1.0, 3.0]
        cols = ['pga', 'psa03', 'psa06', 'psa10', 'psa30']
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
          'psa03', ascending=False), width='stretch')
    with st.expander('¿Cómo leer un espectro?'):
        st.write('Cada línea es una ciudad. Si la curva '
          'es alta en 0.3 s, las casas de 1–3 pisos '
          'sufrieron más; si es alta en 1.0 s, los '
          'edificios medios. Compara ciudades para '
          'priorizar tipo de revisión estructural.')

# ============ SECUNDARIAS ============
elif op == '⛰️ Amenazas secundarias':
    st.title('⛰️ Deslizamientos y licuefacción')
    lectura('<b>Idea clave:</b> el sismo puede '
      'desencadenar otros peligros: <b>deslizamientos</b> '
      'en laderas empinadas y <b>licuefacción</b> en '
      'valles planos y húmedos. Los modelamos con PGA, '
      'pendiente (SRTM) y humedad.')
    capa = st.radio('Capa', [
      'desliz.png', 'liq.png', 'sar.png'],
      horizontal=True,
      format_func=lambda x: {
        'desliz.png': '🟠 Deslizamientos',
        'liq.png': '🔵 Licuefacción',
        'sar.png': '🛰️ Cambio SAR'}[x])
    m = mapa_base()
    overlay(m, capa, 0.75)
    epi(m)
    st_folium(m, height=500)
    if not d_sec.empty:
        a, b = st.columns(2)
        with a:
            fig = px.bar(d_sec.sort_values(
              'km2_desliz').tail(10),
              x='km2_desliz', y='ADM1_NAME',
              orientation='h',
              title='km² susceptibles a deslizamientos')
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')
        with b:
            fig = px.bar(d_sec.sort_values(
              'km2_liq').tail(10),
              x='km2_liq', y='ADM1_NAME',
              orientation='h',
              title='km² susceptibles a licuefacción')
            chart_cfg(fig)
            st.plotly_chart(fig, width='stretch')
    with st.expander('¿Qué es la licuefacción?'):
        st.write('En suelos saturados, la sacudida hace '
          'que el suelo pierda resistencia y se comporte '
          'como un líquido, hundiendo o inclinando '
          'estructuras. Es típica de valles aluviales.')

# ============ APRENDE ============
elif op == '📚 Aprende':
    st.title('📚 Glosario y conceptos')
    lectura('Esta sección explica, sin tecnicismos, '
      'cada término que usas en el observatorio.')
    terms = [
      ('Magnitud (Mw)', 'Energía total liberada. Una '
        'sola cifra por sismo. Cada unidad = ~32× más '
        'energía.'),
      ('Intensidad (MMI)', 'Cuánto se sintió en un '
        'lugar. Va de I a X+ y disminuye con la '
        'distancia.'),
      ('PGA', 'Aceleración máxima del suelo (% de la '
        'gravedad). Mide la "fuerza" del temblor.'),
      ('PSA', 'Aceleración espectral en un período. '
        'Indica qué tipo de edificio resuena más.'),
      ('Exposición', 'Personas o infraestructura en '
        'zonas sacudidas. No implica daño.'),
      ('Susceptibilidad', 'Probabilidad relativa de que '
        'una ladera falle por el sismo.'),
      ('Licuefacción', 'Pérdida de resistencia del suelo '
        'saturado por la sacudida.')]
    for t, d in terms:
        with st.expander(t):
            st.write(d)

# ============ METODOLOGÍA ============
elif op == '🔬 Metodología y datos':
    st.title('🔬 Metodología, fuentes y límites')
    texto = (
        "**Fuentes:** USGS ShakeMap us6000tjl2 · "
        "WorldPop 2020 · ESA WorldCover · VIIRS · "
        "SRTM · CHIRPS · Sentinel-1 · FAO GAUL.\n\n"
        "**Método:** exposición = ShakeMap MMI × "
        "población a escala nativa (100 m); "
        "deslizamientos = PGA × pendiente; "
        "licuefacción = PGA × (1−pendiente) × humedad; "
        "todo calibrado dentro de la zona sacudida "
        "(MMI ≥ 5).\n\n"
        "**Limitaciones:** productos modelados; el "
        "raster MMI cubre el núcleo de sacudida; "
        "réplicas simuladas si la API no publica.")
    st.markdown(texto)
    st.markdown('---')
    st.subheader('Descarga de datos')
    if os.path.exists(D):
        for f in sorted(os.listdir(D)):
            if f.endswith('.csv'):
                try:
                    st.download_button(f,
                      open(f'{D}/{f}', 'rb').read(),
                      file_name=f, key=f)
                except Exception:
                    pass
