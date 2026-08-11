import streamlit as st
import pandas as pd
import numpy as np
import json, os
import folium
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
  page_title='Sismo Colombia 2026',
  layout='wide')
D = 'data'

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
        return json.load(open(p))
    except Exception:
        return {'type': 'FeatureCollection',
                'features': []}

bp = f'{D}/bounds.json'
if os.path.exists(bp):
    B = json.load(open(bp))
    W, S, E, N = B['bounds']
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

st.sidebar.title('🇨🇴 Sismo M7.4')
st.sidebar.caption('Colombia · 10-ago-2026')
op = st.sidebar.radio('Sección', [
  'Resumen ejecutivo',
  'Sismología',
  'Población',
  'Ingeniería',
  'Amenazas secundarias',
  'Validación',
  'Metodología'])

# ---------- helpers de mapa ----------
def mapa_base(zoom=7):
    m = folium.Map(location=[4.9, -76.2],
                   zoom_start=zoom)
    folium.TileLayer(
      'cartodbpositron').add_to(m)
    return m

def overlay(m, png, op_=0.7):
    p = f'{D}/{png}'
    if os.path.exists(p):
        folium.ImageOverlay(
          p, bounds=BOUNDS,
          opacity=op_).add_to(m)

def epi(m):
    folium.Marker(EPI,
      popup='Epicentro M7.4',
      icon=folium.Icon(
        color='red', icon='star')).add_to(m)

# ============ 1. RESUMEN ============
if op == 'Resumen ejecutivo':
    st.title('Resumen ejecutivo')
    st.caption('Terremoto M7.4 · 10-ago-2026 '
      '· San José del Palmar (Chocó)')
    tot = suma(d_exp, 'pob_MMI6plus')
    km2 = suma(d_con, 'km2_const_MMI6')
    n_dep = int((
      d_exp.pob_MMI6plus > 0).sum()) \
      if not d_exp.empty else 0
    n_mun = int((
      d_mun.pob_MMI6plus > 0).sum()) \
      if not d_mun.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Población MMI≥6',
              f'{tot:,.0f}')
    c2.metric('Departamentos', n_dep)
    c3.metric('km² construidos',
              f'{km2:,.0f}')
    c4.metric('Municipios', n_mun)
    m = mapa_base()
    overlay(m, 'intensity_overlay.png')
    epi(m)
    st_folium(m, height=520)
    if not d_exp.empty:
        top = d_exp.sort_values(
          'pob_MMI6plus').tail(10)
        fig = px.bar(top,
          x='pob_MMI6plus', y='ADM1_NAME',
          orientation='h',
          color='pob_MMI6plus',
          color_continuous_scale='Reds')
        fig.update_layout(
          title='Población expuesta (MMI≥6)',
          yaxis_title='',
          xaxis_title='Personas')
        st.plotly_chart(fig,
          use_container_width=True)

# ============ 2. SISMOLOGÍA ============
elif op == 'Sismología':
    st.title('Sismología y réplicas')
    if sint:
        st.warning('Catálogo de réplicas '
          'simulado (Omori–GR): la API USGS '
          'aún no publica datos.')
    feats = rep.get('features', [])
    if not feats:
        st.info('Sin réplicas disponibles.')
    else:
        mags = [f['properties']['mag']
                for f in feats]
        t_h = [f['properties'].get(
          'time_h', 0) for f in feats]
        m = mapa_base()
        for f in feats:
            co = f['geometry']['coordinates']
            mg = f['properties']['mag']
            folium.CircleMarker(
              [co[1], co[0]],
              radius=2 + mg * 1.5,
              color='crimson',
              fill=True,
              fill_opacity=0.5).add_to(m)
        epi(m)
        st_folium(m, height=450)
        a, b = st.columns(2)
        with a:
            fig = px.scatter(x=t_h, y=mags,
              labels={'x': 'Horas desde el '
                'sismo', 'y': 'Magnitud'},
              title='Réplicas en el tiempo')
            st.plotly_chart(fig,
              use_container_width=True)
        with b:
            fig = px.histogram(x=mags,
              nbins=20,
              labels={'x': 'Magnitud'},
              title='Frecuencia–magnitud '
              '(Gutenberg–Richter)')
            st.plotly_chart(fig,
              use_container_width=True)

# ============ 3. POBLACIÓN ============
elif op == 'Población':
    st.title('Exposición poblacional')
    m = mapa_base()
    if not d_exp.empty:
        nrm = Normalize(0,
          d_exp.pob_MMI6plus.max())
        vals = dict(zip(d_exp.ADM1_NAME,
          d_exp.pob_MMI6plus))
        def style(f):
            v = vals.get(
              f['properties']['ADM1_NAME'], 0)
            return {'fillColor': to_hex(
              CMAP(nrm(v))),
              'color': '#444',
              'weight': 0.8,
              'fillOpacity': 0.75}
        folium.GeoJson(dep_gj,
          style_function=style,
          tooltip=folium.GeoJsonTooltip(
            ['ADM1_NAME'])).add_to(m)
    epi(m)
    st_folium(m, height=520)
    a, b = st.columns(2)
    with a:
        if not d_mun.empty:
            top = d_mun.sort_values(
              'pob_MMI6plus').tail(15)
            fig = px.bar(top,
              x='pob_MMI6plus', y='ADM2_NAME',
              orientation='h',
              title='Top municipios expuestos')
            st.plotly_chart(fig,
              use_container_width=True)
    with b:
        if not d_con.empty:
            fig = px.bar(
              d_con.sort_values(
                'km2_const_MMI6').tail(10),
              x='km2_const_MMI6',
              y='ADM1_NAME', orientation='h',
              title='km² construidos (MMI≥6)')
            st.plotly_chart(fig,
              use_container_width=True)

# ============ 4. INGENIERÍA ============
elif op == 'Ingeniería':
    st.title('Ingeniería sísmica')
    st.caption('PSA 0.3s: casas 1–3 pisos · '
      'PSA 1.0s: edificios medios · '
      'PSA 3.0s: puentes y torres')
    if d_ciu.empty:
        st.info('Sin datos de ciudades.')
    else:
        opts = d_ciu.ciudad.tolist()
        defs = [o for o in
          ['Cali', 'Pereira', 'Manizales',
           'Bogota'] if o in opts]
        sel = st.multiselect('Ciudades',
          opts, default=defs)
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
        fig.update_layout(
          xaxis_type='log', yaxis_type='log',
          xaxis_title='Período (s)',
          yaxis_title='Sa (%g)',
          title='Espectros de respuesta')
        st.plotly_chart(fig,
          use_container_width=True)
        st.dataframe(
          d_ciu.sort_values(
            'psa03', ascending=False),
          use_container_width=True)

# ============ 5. SECUNDARIAS ============
elif op == 'Amenazas secundarias':
    st.title('Deslizamientos, licuefacción '
      'y cambio SAR')
    capa = st.radio('Capa', [
      'desliz.png', 'liq.png', 'sar.png'],
      horizontal=True)
    m = mapa_base()
    overlay(m, capa, 0.75)
    epi(m)
    st_folium(m, height=500)
    if d_sec.empty:
        st.info('Sin datos secundarios.')
    else:
        a, b = st.columns(2)
        with a:
            fig = px.bar(
              d_sec.sort_values(
                'km2_desliz').tail(10),
              x='km2_desliz', y='ADM1_NAME',
              orientation='h',
              title='km² susceptibles a '
              'deslizamientos')
            st.plotly_chart(fig,
              use_container_width=True)
        with b:
            fig = px.bar(
              d_sec.sort_values(
                'km2_liq').tail(10),
              x='km2_liq', y='ADM1_NAME',
              orientation='h',
              title='km² susceptibles a '
              'licuefacción')
            st.plotly_chart(fig,
              use_container_width=True)

# ============ 6. VALIDACIÓN ============
elif op == 'Validación':
    st.title('Estaciones: observado vs '
      'modelado')
    if d_est.empty:
        st.info('El catálogo USGS no publica '
          'PGA por estación para este evento; '
          'se muestra el mapa de intensidad.')
        m = mapa_base()
        overlay(m, 'intensity_overlay.png')
        epi(m)
        st_folium(m, height=500)
    else:
        a, b = st.columns(2)
        with a:
            fig = px.scatter(d_est,
              x='pga_mod', y='pga_obs',
              log_x=True, log_y=True,
              labels={'pga_mod': 'PGA modelado '
                '(%g)',
                'pga_obs': 'PGA observado '
                '(%g)'},
              title='Validación ShakeMap')
            mx = float(max(
              d_est.pga_obs.max(),
              d_est.pga_mod.max()))
            mn = float(min(
              d_est.pga_obs.min(),
              d_est.pga_mod.min()))
            mn = max(0.01, mn)
            fig.add_trace(go.Scatter(
              x=[mn, mx], y=[mn, mx],
              mode='lines', name='1:1',
              line={'dash': 'dash'}))
            st.plotly_chart(fig,
              use_container_width=True)
        with b:
            fig = px.scatter(d_est,
              x='dist_km', y='pga_obs',
              log_y=True,
              labels={'dist_km': 'Distancia '
                'epicentral (km)',
                'pga_obs': 'PGA observado '
                '(%g)'},
              title='Atenuación con distancia')
            fig.add_trace(go.Scatter(
              x=d_est.dist_km,
              y=d_est.pga_mod,
              mode='markers',
              name='modelado',
              marker={'symbol': 'x'}))
            st.plotly_chart(fig,
              use_container_width=True)

# ============ 7. METODOLOGÍA ============
elif op == 'Metodología':
    st.title('Metodología y datos')
    st.markdown('''
**Fuentes:** USGS Shake