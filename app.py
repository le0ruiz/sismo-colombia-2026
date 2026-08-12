# =====================================================================
# Observatorio Sísmico Interactivo: Colombia 2026
# Autor: Rafael Leonardo Ruiz Díaz
# Tech Stack: Streamlit, Folium, MapLibre GL, Plotly, GeoPandas, OpenStreetMap
# =====================================================================

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import json, os, struct, math
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go

# Importaciones para mapas interactivos Leaflet
import folium
from streamlit_folium import st_folium
import branca.colormap as bcm

# Configuración inicial de la página
st.set_page_config(
  page_title='Observatorio Sismo Colombia 2026',
  page_icon='🌋', layout='wide')
D = 'data'

# Cargar estilos CSS personalizados
if os.path.exists('style.css'):
    st.markdown('<style>' + open('style.css', encoding='utf-8').read() + '</style>', unsafe_allow_html=True)

# =====================================================================
# FUNCIONES DE CARGA DEFENSIVA
# =====================================================================
def csv_(n):
    p = f'{D}/{n}'
    if not os.path.exists(p): return pd.DataFrame()
    try: return pd.read_csv(p, encoding='utf-8')
    except Exception:
        try: return pd.read_csv(p, encoding='latin-1')
        except Exception: return pd.DataFrame()

def geo_(n):
    p = f'{D}/{n}'
    if not os.path.exists(p): return {'type': 'FeatureCollection', 'features': []}
    try:
        g = json.load(open(p, encoding='utf-8'))
        g['features'] = [f for f in g.get('features', []) if 'coordinates' in f.get('geometry', {})]
        return g
    except Exception: return {'type': 'FeatureCollection', 'features': []}

# =====================================================================
# CONFIGURACIÓN DE LÍMITES GEOGRÁFICOS
# =====================================================================
bp = f'{D}/bounds.json'
if os.path.exists(bp):
    W, S, E, N = json.load(open(bp, encoding='utf-8'))['bounds']
else:
    W, S, E, N = -79.3, 1.8, -73.1, 7.9
BFLAT = [W, S, E, N]

def bounds_png(png, pngw):
    try:
        if not os.path.exists(png) or not os.path.exists(pngw): return None
        with open(png, 'rb') as f: head = f.read(33)
        w, h = struct.unpack('>II', head[16:24])
        with open(pngw, encoding='utf-8') as f: v = [float(x) for x in f.read().split()]
        a, d, b, e, c, ff = v
        left, top = c - a / 2, ff - e / 2
        right, bottom = left + a * w, top + e * h
        if bottom >= top or left >= right: return None
        return [left, bottom, right, top]
    except Exception: return None

BINT = bounds_png(f'{D}/intensity_overlay.png', f'{D}/intensity_overlay.pngw')
if BINT is None: BINT = BFLAT
EPI = [4.903, -76.189]

# =====================================================================
# CONSULTA A OPENSTREETMAP (HOT)
# =====================================================================
@st.cache_data(show_spinner="Consultando infraestructura crítica en OpenStreetMap (HOT)...")
def cargar_infra_osm():
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = """
    [out:json][timeout:50];
    (
      node["amenity"="hospital"](1.8,-79.3,7.9,-73.1);
      way["amenity"="hospital"](1.8,-79.3,7.9,-73.1);
      node["amenity"="school"](1.8,-79.3,7.9,-73.1);
      way["amenity"="school"](1.8,-79.3,7.9,-73.1);
    );
    out center 1000;
    """
    try:
        response = requests.post(overpass_url, data={'data': query}, timeout=60)
        response.raise_for_status()
        data = response.json()
        puntos = []
        for el in data.get('elements', []):
            lat = el.get('lat') or el.get('center', {}).get('lat')
            lon = el.get('lon') or el.get('center', {}).get('lon')
            if lat and lon:
                tags = el.get('tags', {})
                name = tags.get('name', 'Sin nombre')
                amenity = tags.get('amenity', 'desconocido')
                if amenity == 'hospital': color, icon = 'darkred', 'plus'
                elif amenity == 'school': color, icon = 'darkblue', 'graduation-cap'
                else: continue
                puntos.append({'lat': lat, 'lon': lon, 'name': name, 'tipo': amenity, 'color': color, 'icon': icon})
        return puntos
    except Exception: return []

osm_infra = cargar_infra_osm()

# =====================================================================
# CACHÉ DE DATOS LOCALES
# =====================================================================
@st.cache_data
def cargar_datos():
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
        if not d_exp.empty and 'ADM1_NAME' in d_exp.columns:
            possible_cols = ['ADM1_NAME', 'NOMBRE_DEP', 'NOMBRE', 'DPTO_NOMBRE']
            name_col = None
            for col in possible_cols:
                if col in g_dep.columns: name_col = col; break
            if name_col:
                g_dep['merge_col'] = g_dep[name_col].astype(str).str.upper().str.strip()
                d_exp['merge_col'] = d_exp['ADM1_NAME'].astype(str).str.upper().str.strip()
                d_exp_clean = d_exp[['merge_col', 'pob_MMI6plus']].rename(columns={'pob_MMI6plus': 'Pob_Exp'})
                g_dep = g_dep.merge(d_exp_clean, on='merge_col', how='left')
                if name_col != 'ADM1_NAME': g_dep['ADM1_NAME'] = g_dep[name_col]
    except Exception: g_dep = None
        
    return d_exp, d_mun, d_con, d_sec, d_ciu, d_est, rep, sint, g_dep

d_exp, d_mun, d_con, d_sec, d_ciu, d_est, rep, sint, g_dep = cargar_datos()

AUTOR = ('Ensayo desarrollado por <b>Rafael Leonardo Ruiz Díaz</b> · un aporte para entender el sismo')
MMI = [
  ('IV', '#67a3ff', 'Moderado', 'Vibración como el paso de un camión.'),
  ('V', '#2ee6a8', 'Fuerte', 'Despierta a dormidos; caen objetos.'),
  ('VI', '#f9f759', 'Fuerte+', 'Grietas en muros; daño leve.'),
  ('VII', '#fcb448', 'Muy fuerte', 'Daño moderado en edificaciones.'),
  ('VIII', '#fb8b2c', 'Severo', 'Daño considerable; pánico.'),
  ('IX', '#e31a1c', 'Violento', 'Colapsos parciales y totales.')]

# =====================================================================
# HELPERS Y FORMATO ESPAÑOL
# =====================================================================
def fmt(x, dec=0):
    if pd.isna(x) or x is None: return '0'
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def suma(df, col):
    if df.empty or col not in df: return 0.0
    return float(df[col].sum())

def lectura(txt):
    st.markdown('<div class="lectura">' + txt + '</div>', unsafe_allow_html=True)

def chart_cfg(fig):
    fig.update_layout(
        template='plotly_white', font=dict(family='Inter', size=12, color='#12263f'),
        margin=dict(l=20, r=20, t=50, b=20), separators='.,'
    )

# =====================================================================
# MAPA LEAFLET INTERACTIVO
# =====================================================================
def mapa_interactivo(titulo, capa=None, bb=None, coro=None, items=None, nota=None, puntos=None, infra=None):
    m = folium.Map(location=[EPI[0], EPI[1]], zoom_start=6, tiles='CartoDB positron', control_scale=True)

    if g_dep is not None:
        if coro is None:
            folium.GeoJson(
                json.loads(g_dep.to_json()), name='Departamentos',
                style_function=lambda x: {'fillColor': 'transparent', 'color': '#93a1b5', 'weight': 0.7, 'fillOpacity': 0.1},
                tooltip=folium.GeoJsonTooltip(fields=['ADM1_NAME'], aliases=['Depto:']) if 'ADM1_NAME' in g_dep.columns else None
            ).add_to(m)
        else:
            g_dep_temp = g_dep.copy()
            if 'Pob_Exp' not in g_dep_temp.columns: g_dep_temp['Pob_Exp'] = coro
            else: g_dep_temp['Pob_Exp'] = g_dep_temp['Pob_Exp'].fillna(0)
            
            g_dep_temp['Pob_Exp_Fmt'] = g_dep_temp['Pob_Exp'].apply(lambda v: fmt(v))
            max_v = max(coro) if max(coro) > 0 else 1
            colormap = bcm.linear.Reds_09.scale(0, max_v)
            folium.GeoJson(
                json.loads(g_dep_temp.to_json()), name='Población expuesta',
                style_function=lambda feature: {'fillColor': colormap(feature['properties'].get('Pob_Exp', 0)), 'color': '#8895a8', 'weight': 0.5, 'fillOpacity': 0.7},
                tooltip=folium.GeoJsonTooltip(
                    fields=['ADM1_NAME', 'Pob_Exp_Fmt'] if 'ADM1_NAME' in g_dep_temp.columns else ['Pob_Exp_Fmt'], 
                    aliases=['Departamento:', 'Pob. Expuesta:'], localize=True, sticky=False, labels=True,
                    style="background-color: #F0EFEF; border: 2px solid black; border-radius: 3px; box-shadow: 3px;", max_width=800
                )
            ).add_to(m)
            m.add_child(colormap)

    if capa:
        p = f'{D}/{capa}'
        if os.path.exists(p):
            img = plt.imread(p)
            b = bb or BFLAT
            bounds = [[b[1], b[0]], [b[3], b[2]]]
            folium.raster_layers.ImageOverlay(image=img, bounds=bounds, opacity=0.85, name=capa, interactive=False, cross_origin=False, zindex=1).add_to(m)
            m.fit_bounds(bounds)
        else: st.caption('⚠️ Falta: ' + capa)

    if puntos:
        fg_rep = folium.FeatureGroup(name='♻️ Réplicas')
        for lon, lat, r in puntos:
            folium.CircleMarker(location=[lat, lon], radius=r, color='white', weight=0.6, fill=True, fill_color='#d10000', fill_opacity=0.7).add_to(fg_rep)
        fg_rep.add_to(m)

    if infra:
        fg_hosp = folium.FeatureGroup(name='🏥 Hospitales (OSM)')
        fg_esc = folium.FeatureGroup(name='🏫 Escuelas (OSM)')
        for p in infra:
            marker = folium.Marker(location=[p['lat'], p['lon']], tooltip=f"<b>{p['name']}</b><br>Tipo: {p['tipo'].capitalize()}", icon=folium.Icon(color=p['color'], icon=p['icon'], prefix='fa'))
            if p['tipo'] == 'hospital': marker.add_to(fg_hosp)
            else: marker.add_to(fg_esc)
        fg_hosp.add_to(m); fg_esc.add_to(m)

    folium.Marker(location=[EPI[0], EPI[1]], tooltip='Epicentro (M7.4)', icon=folium.Icon(color='red', icon='star', prefix='fa')).add_to(m)

    if items:
        legend_html = """<div style="position: fixed; bottom: 40px; left: 40px; z-index: 9999; background-color: white; padding: 10px; border-radius: 5px; border: 1px solid #8895a8; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);"><h6 style="margin:0 0 5px 0; color:#0b1f3a; font-weight:bold;">""" + titulo + """</h6>"""
        for c, t in items:
            legend_html += f"""<div style="margin: 2px 0; color: #12263f; font-size: 12px;"><span style="display:inline-block; width:14px; height:14px; background:{c}; border:1px solid #444; margin-right:5px; vertical-align:middle;"></span>{t}</div>"""
        if nota: legend_html += f"<hr style='margin:5px 0;'><i style='font-size:10px;color:#46587a;'>{nota}</i>"
        legend_html += "</div>"
        m.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl(collapsed=False).add_to(m)
    st_folium(m, width=None, height=500, returned_objects=[])

# =====================================================================
# SECCIONES DE LA APP
# =====================================================================
def sec_inicio():
    st.markdown('<div class="hero"><h1 style="color:#ffffff !important;">Terremoto de Colombia M7.4</h1><p>Observatorio ciudadano de exposición y riesgo · 10 de agosto de 2026</p><span class="badge">USGS ShakeMap</span><span class="badge">WorldPop</span><span class="badge">HOT / OpenStreetMap</span><div class="autor">' + AUTOR + '</div></div>', unsafe_allow_html=True)
    lectura('<b>¿Qué es este sitio?</b> Un panel interactivo que traduce los datos técnicos del sismo en información comprensible: cuántas personas sintieron el temblor, qué zonas pueden sufrir deslizamientos y qué ciudades deben priorizar revisiones.')
    
    tot, km2 = suma(d_exp, 'pob_MMI6plus'), suma(d_con, 'km2_const_MMI6')
    n_dep = int((d_exp.pob_MMI6plus > 0).sum()) if not d_exp.empty else 0
    n_mun = int((d_mun.pob_MMI6plus > 0).sum()) if not d_mun.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Personas con sacudida fuerte', fmt(tot)); c2.metric('Departamentos afectados', fmt(n_dep))
    c3.metric('Municipios afectados', fmt(n_mun)); c4.metric('km² urbanos expuestos', fmt(km2))
    st.markdown('---')
    
    mapa_interactivo('Intensidad (MMI)', capa='intensity_overlay.png', bb=BINT, items=[(x[1], x[0] + ' ' + x[2]) for x in MMI], nota='Render oficial USGS ShakeMap · estrella = epicentro', infra=osm_infra)
    lectura('<b>Cómo leer el mapa:</b> los colores cálidos (amarillo→rojo) indican sacudida más fuerte; la estrella es el epicentro. Activa las capas de hospitales y escuelas en la esquina superior derecha para ver la infraestructura expuesta.')

def sec_sismo():
    st.title('🌍 El sismo en contexto')
    lectura('<b>Resumen:</b> un sismo de magnitud 7.4 con hipocentro profundo (~107 km) bajo el Chocó. Al ser profundo, la sacudida se sintió en un área muy amplia, pero el daño extremo quedó más localizado que en un sismo superficial.')
    a, b = st.columns(2)
    with a: st.metric('Magnitud (Mw)', '7,4'); st.metric('Profundidad', '~107 km')
    with b: st.metric('Epicentro', '4,90°N, 76,19°O'); st.metric('Fecha', '10-ago-2026')
    st.markdown('---'); st.subheader('Réplicas')
    if sint: st.warning('Catálogo ilustrativo (Omori–GR): la API del USGS aún no publica réplicas.')
    
    feats = rep.get('features', [])
    if feats:
        mags = [f['properties']['mag'] for f in feats]; t_h = [f['properties'].get('time_h', 0) for f in feats]
        pts = [(f['geometry']['coordinates'][0], f['geometry']['coordinates'][1], 1.5 + f['properties']['mag'] * 1.2) for f in feats]
        mapa_interactivo('Réplicas', puntos=pts, items=[('#d10000', 'Réplicas (tamaño = magnitud)')], nota='Catálogo Omori–GR', infra=osm_infra)
        c1, c2 = st.columns(2)
        with c1:
            fig = px.scatter(x=t_h, y=mags, labels={'x': 'Horas desde el sismo', 'y': 'Magnitud'}, title='Réplicas en el tiempo')
            chart_cfg(fig); st.plotly_chart(fig, width='stretch')
        with c2:
            fig = px.histogram(x=mags, nbins=20, labels={'x': 'Magnitud'}, title='Frecuencia–magnitud')
            chart_cfg(fig); st.plotly_chart(fig, width='stretch')

def sec_3d():
    st.title('🌐 Terreno 3D · Vista Google Earth')
    lectura('<b>Relieve real con hillshade:</b> navega libremente por la Cordillera Occidental. Activa o desactiva capas, inclina la camara y explora como lo harias en Google Earth. Los datos de elevacion provienen del SRTM.')

    ciudades = []
    if not d_ciu.empty and 'ciudad' in d_ciu.columns:
        for _, r in d_ciu.iterrows():
            try:
                ciudades.append({
                    'name': str(r['ciudad']),
                    'lat': float(r.get('lat', r.get('latitude', 0))),
                    'lon': float(r.get('lon', r.get('longitude', 0))),
                    'pop': int(r.get('pob_MMI6plus', r.get('poblacion', 0))),
                    'psa03': float(r.get('psa03', 0)),
                })
            except: pass
    if not ciudades:
        ciudades = [
            {'name': 'Pereira', 'lat': 4.813, 'lon': -75.696, 'pop': 467269, 'psa03': 0.18},
            {'name': 'Manizales', 'lat': 5.069, 'lon': -75.518, 'pop': 400000, 'psa03': 0.22},
            {'name': 'Armenia', 'lat': 4.533, 'lon': -75.681, 'pop': 300000, 'psa03': 0.15},
            {'name': 'Cali', 'lat': 3.452, 'lon': -76.532, 'pop': 2227000, 'psa03': 0.08},
            {'name': 'Bogota', 'lat': 4.711, 'lon': -74.072, 'pop': 7181000, 'psa03': 0.05},
            {'name': 'Medellin', 'lat': 6.252, 'lon': -75.563, 'pop': 2500000, 'psa03': 0.06},
            {'name': 'Ibague', 'lat': 4.437, 'lon': -75.202, 'pop': 529000, 'psa03': 0.12},
            {'name': 'San Jose del Palmar', 'lat': 4.970, 'lon': -76.229, 'pop': 2392, 'psa03': 0.45},
            {'name': 'Ansermanuevo', 'lat': 4.797, 'lon': -75.995, 'pop': 12332, 'psa03': 0.35},
        ]

    # Convertir ciudades a GeoJSON FeatureCollection para MapLibre
    geojson_ciudades = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [c['lon'], c['lat']]},
                "properties": {"name": c['name'], "pop": c['pop'], "psa03": c['psa03']}
            } for c in ciudades
        ]
    }
    ciudades_json = json.dumps(geojson_ciudades)
    epi_lat, epi_lon = EPI[0], EPI[1]
    w, s, e, n = W, S, E, N

    maplibre_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <script src="https://unpkg.com/maplibre-gl@4.1.0/dist/maplibre-gl.js"></script>
    <link href="https://unpkg.com/maplibre-gl@4.1.0/dist/maplibre-gl.css" rel="stylesheet"/>
    <style>
        html, body { margin:0; padding:0; height:100%; overflow:hidden; font-family: 'Segoe UI', sans-serif; background:#0f172a; }
        #map { position:absolute; top:0; left:0; width:100%; height:100%; }
        .panel { position:absolute; top:10px; left:10px; background:rgba(15,23,42,0.92); backdrop-filter:blur(10px); border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:12px 14px; color:#fff; max-width:230px; z-index:10; box-shadow:0 4px 20px rgba(0,0,0,0.4); }
        .panel h3 { margin:0 0 6px 0; font-size:14px; font-weight:500; }
        .panel .meta { font-size:11px; color:rgba(255,255,255,0.5); margin-bottom:8px; }
        .panel .row { display:flex; gap:14px; margin-top:6px; }
        .panel .row div { font-size:11px; }
        .panel .row div span { display:block; color:rgba(255,255,255,0.4); font-size:9px; text-transform:uppercase; letter-spacing:0.5px; }
        .legend { position:absolute; bottom:10px; right:10px; background:rgba(15,23,42,0.92); backdrop-filter:blur(10px); border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:10px 12px; color:#fff; z-index:10; box-shadow:0 4px 20px rgba(0,0,0,0.4); }
        .legend h4 { margin:0 0 6px 0; font-size:11px; font-weight:500; color:rgba(255,255,255,0.7); }
        .legend .item { display:flex; align-items:center; gap:6px; margin-bottom:4px; font-size:10px; color:rgba(255,255,255,0.6); }
        .legend .dot { width:10px; height:10px; border-radius:2px; }
        .ctrl { position:absolute; top:10px; right:10px; background:rgba(15,23,42,0.92); backdrop-filter:blur(10px); border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:8px; z-index:10; display:flex; flex-direction:column; gap:4px; }
        .ctrl button { background:transparent; border:1px solid rgba(255,255,255,0.12); border-radius:6px; color:rgba(255,255,255,0.7); padding:5px 10px; font-size:11px; cursor:pointer; font-family:inherit; transition:all 0.15s; }
        .ctrl button:hover { background:rgba(255,255,255,0.08); }
        .ctrl button.active { background:rgba(255,255,255,0.15); color:#fff; border-color:rgba(255,255,255,0.3); }
        .badge { position:absolute; bottom:10px; left:10px; background:rgba(15,23,42,0.7); border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:3px 10px; color:rgba(255,255,255,0.35); font-size:9px; z-index:10; }
        .maplibregl-ctrl-group { background:rgba(15,23,42,0.9) !important; border:1px solid rgba(255,255,255,0.12) !important; border-radius:8px !important; overflow:hidden; }
        .maplibregl-ctrl-group button { background:rgba(15,23,42,0.9) !important; color:rgba(255,255,255,0.7) !important; border-color:rgba(255,255,255,0.08) !important; }
        .maplibregl-popup-content { background:rgba(15,23,42,0.95) !important; color:#fff !important; border:1px solid rgba(255,255,255,0.1); border-radius:8px !important; font-size:12px; padding:8px 12px !important; box-shadow:0 4px 20px rgba(0,0,0,0.4) !important; }
        .maplibregl-popup-tip { border-top-color:rgba(15,23,42,0.95) !important; }
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="panel">
        <h3>🌋 Epicentro M7.4</h3>
        <div class="meta">San Jose del Palmar, Choco &middot; 10 ago 2026</div>
        <div class="row">
            <div><span>Latitud</span>__EPI_LAT__°N</div>
            <div><span>Longitud</span>__EPI_LON_ABS__°O</div>
        </div>
        <div class="row">
            <div><span>Profundidad</span>107 km</div>
            <div><span>Magnitud</span>Mw 7.4</div>
        </div>
    </div>
    <div class="ctrl">
        <button id="btn-terrain" class="active" onclick="toggleTerrain()">⛰️ Terreno 3D</button>
        <button id="btn-hillshade" class="active" onclick="toggleHillshade()">🌑 Hillshade</button>
        <button id="btn-sat" onclick="toggleSat()">🛰️ Satelite</button>
        <button onclick="resetView()">⌖ Centrar</button>
    </div>
    <div class="legend">
        <h4>Elevacion (m s.n.m.)</h4>
        <div class="item"><div class="dot" style="background:#1e3a5f;"></div>0 &ndash; 500 (Valles/Pacifico)</div>
        <div class="item"><div class="dot" style="background:#2d5a3c;"></div>500 &ndash; 1500 (Laderas)</div>
        <div class="item"><div class="dot" style="background:#5a7a4a;"></div>1500 &ndash; 2500 (Montana media)</div>
        <div class="item"><div class="dot" style="background:#8aaa6a;"></div>2500 &ndash; 3500 (Montana alta)</div>
        <div class="item"><div class="dot" style="background:#c0daa0;"></div>3500+ (Paramo/nieves)</div>
    </div>
    <div class="badge">MapLibre GL &middot; DEM: AWS Terrain Tiles &middot; Hillshade</div>
    <script>
        const ciudades = __CIUDADES_JSON__;
        const epi = [__EPI_LON__, __EPI_LAT__];
        
        const styleBase = {
            version: 8,
            sources: {
                osm: { type: 'raster', tiles: ['https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'], tileSize: 256, attribution: '&copy; OSM &copy; CARTO' },
                satellite: { type: 'raster', tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'], tileSize: 256, attribution: '&copy; Esri' },
                terrainSource: { 
                    type: 'raster-dem', 
                    tiles: ['https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png'], 
                    tileSize: 256, 
                    encoding: 'terrarium',
                    maxzoom: 14
                },
                hillshadeSource: { 
                    type: 'raster-dem', 
                    tiles: ['https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png'], 
                    tileSize: 256, 
                    encoding: 'terrarium',
                    maxzoom: 14
                }
            },
            layers: [
                { id: 'osm', type: 'raster', source: 'osm' },
                { id: 'hillshade', type: 'hillshade', source: 'hillshadeSource', paint: { 'hillshade-exaggeration': 0.8, 'hillshade-shadow-color': '#000000', 'hillshade-highlight-color': '#ffffff', 'hillshade-accent-color': '#333333', 'hillshade-illumination-anchor': 'viewport', 'hillshade-illumination-direction': 315 } }
            ]
        };
        
        const map = new maplibregl.Map({ container: 'map', style: styleBase, center: epi, zoom: 8.5, pitch: 60, bearing: -30, maxPitch: 85, antialias: true });
        
        map.addControl(new maplibregl.NavigationControl({ visualizePitch: true, showZoom: true, showCompass: true }), 'bottom-right');
        map.addControl(new maplibregl.ScaleControl({ maxWidth: 100, unit: 'metric' }), 'bottom-left');
        
        map.on('load', () => {
            // Forzar terreno
            map.setTerrain({ source: 'terrainSource', exaggeration: 1.5 });
            
            // Capa del epicentro (Círculo nativo de MapLibre para garantizar visibilidad)
            map.addSource('epi', { type: 'geojson', data: { type: 'Point', coordinates: epi } });
            map.addLayer({
                id: 'epi-circle',
                type: 'circle',
                source: 'epi',
                paint: {
                    'circle-radius': 8,
                    'circle-color': '#ff3333',
                    'circle-stroke-width': 2,
                    'circle-stroke-color': '#ffffff'
                }
            });

            // Capa de ciudades (Círculos nativos de MapLibre)
            map.addSource('ciudades', { type: 'geojson', data: ciudades });
            map.addLayer({
                id: 'ciudades-circle',
                type: 'circle',
                source: 'ciudades',
                paint: {
                    'circle-radius': 6,
                    'circle-color': ['case', ['>', ['get', 'psa03'], 0.2], '#ff8844', ['>', ['get', 'psa03'], 0.1], '#ffcc44', '#44aaff'],
                    'circle-stroke-width': 1.5,
                    'circle-stroke-color': '#ffffff'
                }
            });

            // Popups interactivos
            const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
            
            map.on('mouseenter', 'epi-circle', () => { map.getCanvas().style.cursor = 'pointer'; });
            map.on('mousemove', 'epi-circle', (e) => {
                popup.setLngLat(epli).setHTML('<b>Epicentro M7.4</b><br>Profundidad: 107 km').addTo(map);
            });
            map.on('mouseleave', 'epi-circle', () => { map.getCanvas().style.cursor = ''; popup.remove(); });

            map.on('mouseenter', 'ciudades-circle', () => { map.getCanvas().style.cursor = 'pointer'; });
            map.on('mousemove', 'ciudades-circle', (e) => {
                const f = e.features[0];
                popup.setLngLat(f.geometry.coordinates).setHTML(`<b>${f.properties.name}</b><br>Poblacion expuesta: ${f.properties.pop}<br>PSA 0.3s: ${f.properties.psa03}g`).addTo(map);
            });
            map.on('mouseleave', 'ciudades-circle', () => { map.getCanvas().style.cursor = ''; popup.remove(); });

            map.addSource('bounds', { type: 'geojson', data: { type: 'Feature', geometry: { type: 'Polygon', coordinates: [[[__W__,__S__],[__E__,__S__],[__E__,__N__],[__W__,__N__],[__W__,__S__]]] } } });
            map.addLayer({ id: 'bounds-line', type: 'line', source: 'bounds', paint: { 'line-color': 'rgba(100,180,255,0.3)', 'line-width': 1, 'line-dasharray': [3,3] } });
        });
        
        let terrainOn = true, hillOn = true, satOn = false;
        
        function toggleTerrain(){ 
            terrainOn = !terrainOn; 
            map.setTerrain(terrainOn ? {source:'terrainSource', exaggeration:1.5} : null); 
            document.getElementById('btn-terrain').classList.toggle('active', terrainOn); 
        }
        
        function toggleHillshade(){ 
            hillOn = !hillOn; 
            map.setLayoutProperty('hillshade', 'visibility', hillOn ? 'visible' : 'none'); 
            document.getElementById('btn-hillshade').classList.toggle('active', hillOn); 
        }
        
        function toggleSat(){ 
            satOn = !satOn; 
            if(satOn){ 
                map.setLayoutProperty('osm', 'visibility', 'none'); 
                if(!map.getLayer('sat')) map.addLayer({id:'sat', type:'raster', source:'satellite'}, 'hillshade'); 
                else map.setLayoutProperty('sat', 'visibility', 'visible'); 
            } else { 
                map.setLayoutProperty('osm', 'visibility', 'visible'); 
                if(map.getLayer('sat')) map.setLayoutProperty('sat', 'visibility', 'none'); 
            } 
            document.getElementById('btn-sat').classList.toggle('active', satOn); 
        }
        
        function resetView(){ 
            map.flyTo({center:epi, zoom:8.5, pitch:60, bearing:-30, duration:1500}); 
        }
    </script>
</body>
</html>"""
    
    maplibre_html = maplibre_html.replace("__CIUDADES_JSON__", str(ciudades_json))
    maplibre_html = maplibre_html.replace("__EPI_LAT__", str(epi_lat))
    maplibre_html = maplibre_html.replace("__EPI_LON__", str(epi_lon))
    maplibre_html = maplibre_html.replace("__EPI_LON_ABS__", str(abs(epi_lon)))
    maplibre_html = maplibre_html.replace("__W__", str(w))
    maplibre_html = maplibre_html.replace("__S__", str(s))
    maplibre_html = maplibre_html.replace("__E__", str(e))
    maplibre_html = maplibre_html.replace("__N__", str(n))

    components.html(maplibre_html, height=650, scrolling=False)

    st.markdown('---')
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.metric('Elevacion maxima', '~4.700 m', help='Nevado del Huila')
    with c2: st.metric('Pendiente media', '~18 deg', help='Cordillera Occidental')
    with c3: st.metric('Ciudades en mapa', len(ciudades), help='Principales centros urbanos')
    with c4: st.metric('Resolucion DEM', '30 m', help='SRTM 1 arc-sec')
    with c5: st.metric('Exageracion vertical', '1.5x', help='Realce del relieve para visualizacion')

    guia_col, leyenda_col = st.columns([3, 2])
    with guia_col:
        st.markdown("""
        <div style="background:#f8f9fa; border-radius:10px; padding:16px; border:1px solid #dee2e6;">
            <h4 style="margin:0 0 10px 0; color:#12263f; font-size:15px;">Como navegar el mapa 3D</h4>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:13px; color:#46587a;">
                <div>🖱️ <b>Click derecho + arrastra</b> &rarr; Rotar / inclinar</div>
                <div>🔄 <b>Rueda del raton</b> &rarr; Zoom in/out</div>
                <div>👆 <b>Click + arrastra</b> &rarr; Pan (mover mapa)</div>
                <div>📐 <b>Ctrl + arrastra</b> &rarr; Inclinar camara</div>
            </div>
            <p style="margin:10px 0 0 0; font-size:12px; color:#6c757d;">
                Usa los botones superiores derechos del mapa para activar/desactivar <b>terreno 3D</b>, <b>hillshade</b> o <b>vista satelital</b>.
                El hillshade resalta el relieve con sombras dinamicas segun la inclinacion de la camara.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with leyenda_col:
        st.markdown("""
        <div style="background:#f8f9fa; border-radius:10px; padding:16px; border:1px solid #dee2e6;">
            <h4 style="margin:0 0 10px 0; color:#12263f; font-size:15px;">Simbolos en el mapa</h4>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;"><div style="width:12px; height:12px; border-radius:50%; background:#ff3333; border:2px solid #ffaaaa;"></div><span style="font-size:12px; color:#46587a;">Epicentro M7.4 (pulso)</span></div>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;"><div style="width:10px; height:10px; border-radius:50%; background:#ff8844; border:2px solid #fff;"></div><span style="font-size:12px; color:#46587a;">Ciudad alta sacudida (PSA &gt;0.2g)</span></div>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;"><div style="width:10px; height:10px; border-radius:50%; background:#ffcc44; border:2px solid #fff;"></div><span style="font-size:12px; color:#46587a;">Ciudad media sacudida</span></div>
            <div style="display:flex; align-items:center; gap:8px;"><div style="width:10px; height:10px; border-radius:50%; background:#44aaff; border:2px solid #fff;"></div><span style="font-size:12px; color:#46587a;">Ciudad baja sacudida</span></div>
        </div>
        """, unsafe_allow_html=True)
    st.caption('💡 **Nota tecnica:** El mapa usa MapLibre GL con terrain 3D y hillshade dinamico. La exageracion vertical de 1.5x realza el relieve sin distorsionar la geografia.')

def sec_comparativa():
    st.title('🆚 Dos sismos, dos historias')
    lectura('<b>Más allá de la magnitud:</b> por qué sismos de tamaño similar pueden generar impactos radicalmente diferentes. De la roca a la ciudad.')
    a, b = st.columns(2)
    with a: st.markdown('<div class="card card-col"><h3>🏔️ Caso Colombia · 10-ago-2026</h3><b>Mw 7.4 · Profundidad ~107 km</b><ul class="mini"><li><b>Ruptura profunda:</b> mayor recorrido de las ondas hasta la superficie.</li><li><b>Mayor dispersión:</b> las ondas se atenúan significativamente antes de llegar.</li><li><b>Área afectada:</b> movimiento perceptible en una región muy extensa, con menor violencia puntual.</li></ul></div>', unsafe_allow_html=True)
    with b: st.markdown('<div class="card card-ven"><h3>🏙️ Caso Venezuela · 24-jun-2026</h3><b>Doblete Mw 7.2 + 7.5 · ~10–20 km</b><ul class="mini"><li><b>Ruptura somera:</b> muy próxima a zonas urbanas.</li><li><b>Menor atenuación:</b> las ondas golpean con mayor energía.</li><li><b>Doblete sísmico:</b> dos demandas sucesivas sobre estructuras posiblemente degradadas por el primer evento.</li></ul></div>', unsafe_allow_html=True)
    
    st.markdown('---'); c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(x=['Colombia', 'Venezuela'], y=[107, 15], labels={'y': 'Profundidad (km)', 'x': ''}, title='Profundidad del hipocentro', color=['Colombia', 'Venezuela'], color_discrete_map={'Colombia': '#2563eb', 'Venezuela': '#ea580c'})
        chart_cfg(fig); st.plotly_chart(fig, width='stretch')
    with c2:
        ds = list(range(10, 301, 10))
        som = [120 * math.exp(-d / 90) + 4 for d in ds]; prof = [70 * math.exp(-d / 160) + 3 for d in ds]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ds, y=som, mode='lines', name='Somero (VEN)', line={'color': '#ea580c', 'width': 3}))
        fig.add_trace(go.Scatter(x=ds, y=prof, mode='lines', name='Profundo (COL)', line={'color': '#2563eb', 'width': 3}))
        fig.update_layout(title='Atenuación con la distancia (esquemático)', xaxis_title='Distancia a la ruptura (km)', yaxis_title='Sacudida relativa')
        chart_cfg(fig); st.plotly_chart(fig, width='stretch')
    st.caption('Gráfico esquemático didáctico: un sismo somero concentra daño extremo cerca de la falla; uno profundo reparte sacudida moderada en un área amplia.')
    
    st.subheader('El suelo transforma la sacudida')
    a, b = st.columns(2)
    with a: st.markdown('<div class="card card-suelo"><h3>🏜️ Cuenca y topografía</h3><ul class="mini"><li>El contraste de rigidez de los estratos refleja, refracta y filtra las ondas.</li><li><b>Depósitos blandos:</b> posible amplificación y mayor duración.</li><li><b>Cuencas:</b> reflejo y atrapamiento de ondas.</li><li><b>Relieves:</b> concentración o dispersión según su geometría.</li></ul></div>', unsafe_allow_html=True)
    with b: st.markdown('<div class="card card-suelo"><h3>💦 Licuación de suelos</h3><ul class="mini"><li>Pérdida súbita de resistencia del terreno.</li><li>Requiere: suelo granular suelto + saturación de agua + demanda cíclica fuerte.</li><li>Las estructuras pueden hundirse o inclinarse por pérdida de soporte.</li></ul></div>', unsafe_allow_html=True)
        
    st.subheader('Cada estructura "escucha" un sismo diferente')
    a, b, c = st.columns(3)
    with a: st.markdown('<div class="card card-col"><h3>🏠 Bajas (1–3 pisos)</h3><p class="mini">Responden con mayor fuerza a ondas de periodo corto (alta frecuencia, ~0.3 s).</p></div>', unsafe_allow_html=True)
    with b: st.markdown('<div class="card card-col"><h3>🏢 Medianas</h3><p class="mini">Más sensibles a ondas de periodo intermedio (~1.0 s).</p></div>', unsafe_allow_html=True)
    with c: st.markdown('<div class="card card-col"><h3>🏙️ Altas</h3><p class="mini">Entran en resonancia con ondas de periodo largo (baja frecuencia, ~3.0 s).</p></div>', unsafe_allow_html=True)
        
    lectura('<b>Compatibilidad espectral:</b> si el suelo amplifica periodos cercanos al periodo natural de una estructura, su respuesta y el daño pueden aumentar dramáticamente. <b>Misma magnitud ≠ misma demanda</b> para todos los edificios.')
    st.markdown('<div class="risk-banner">Riesgo Sísmico = Amenaza × Exposición × Vulnerabilidad</div>', unsafe_allow_html=True)

def sec_intensidad():
    st.title('🎯 ¿Con qué fuerza se sintió?')
    lectura('<b>Idea clave:</b> la <b>magnitud</b> es la energía liberada (una sola cifra); la <b>intensidad (MMI)</b> es cuánto se sintió en cada lugar (varía con la distancia).')
    st.subheader('Escala de Mercalli Modificada')
    cols = st.columns(len(MMI))
    for i, (num, col, nom, desc) in enumerate(MMI):
        with cols[i]: st.markdown('<div class="mmi-chip" style="background:' + col + '"><span class="num">' + num + '</span><b>' + nom + '</b><br>' + desc + '</div>', unsafe_allow_html=True)
    st.markdown('---')
    mapa_interactivo('Intensidad (MMI)', capa='intensity_overlay.png', bb=BINT, items=[(x[1], x[0] + ' ' + x[2]) for x in MMI], nota='Render oficial USGS ShakeMap, alineado con su world file (.pngw)', infra=osm_infra)

def sec_poblacion():
    st.title('👥 ¿Cuántas personas fueron expuestas?')
    lectura('<b>Idea clave:</b> cruzamos el mapa de intensidad con el mapa de población (WorldPop, 100 m) para estimar cuántas personas viven en zonas con cada nivel de sacudida.')
    tot = suma(d_exp, 'pob_MMI6plus'); st.metric('Población con MMI ≥ 6', fmt(tot))
    coro = None
    if g_dep is not None and not d_exp.empty:
        vals = dict(zip(d_exp.ADM1_NAME, d_exp.pob_MMI6plus))
        coro = [vals.get(n, 0) for n in g_dep.ADM1_NAME] if 'ADM1_NAME' in g_dep.columns else None
    items = [('#fee5d9', 'Baja'), ('#fb6a4a', 'Media'), ('#a50f15', 'Alta')]
    mapa_interactivo('Población expuesta', coro=coro, items=items, nota='Coropleta: personas en MMI ≥ 6 por departamento', infra=osm_infra)
    a, b = st.columns(2)
    with a:
        if not d_exp.empty:
            top = d_exp.sort_values('pob_MMI6plus').tail(10)
            fig = px.bar(top, x='pob_MMI6plus', y='ADM1_NAME', orientation='h', color='pob_MMI6plus', color_continuous_scale='Reds', title='Departamentos más expuestos')
            chart_cfg(fig); st.plotly_chart(fig, width='stretch')
    with b:
        if not d_mun.empty:
            top = d_mun.sort_values('pob_MMI6plus').tail(15)
            fig = px.bar(top, x='pob_MMI6plus', y='ADM2_NAME', orientation='h', title='Municipios más expuestos')
            chart_cfg(fig); st.plotly_chart(fig, width='stretch')

def sec_edificaciones():
    st.title('🏗️ Edificaciones e ingeniería')
    lectura('<b>Idea clave:</b> distintas estructuras resuenan con distintos períodos. Las <b>PSA</b> miden la sacudida en cada período: 0.3 s casas bajas, 1.0 s edificios medios, 3.0 s puentes y torres.')
    km2 = suma(d_con, 'km2_const_MMI6'); st.metric('km² urbanos en MMI ≥ 6', fmt(km2))
    if not d_con.empty:
        fig = px.bar(d_con.sort_values('km2_const_MMI6').tail(10), x='km2_const_MMI6', y='ADM1_NAME', orientation='h', title='Huella urbana expuesta por departamento')
        chart_cfg(fig); st.plotly_chart(fig, width='stretch')
    st.markdown('---'); st.subheader('Espectros de respuesta por ciudad')
    if not d_ciu.empty:
        opts = d_ciu.ciudad.tolist(); defs = [o for o in ['Cali', 'Pereira', 'Manizales', 'Bogota'] if o in opts]
        sel = st.multiselect('Ciudades', opts, default=defs)
        TS = [0.03, 0.3, 0.6, 1.0, 3.0]; cols = ['pga', 'psa03', 'psa06', 'psa10', 'psa30']
        fig = go.Figure()
        for c in sel:
            rr = d_ciu[d_ciu.ciudad == c]
            if rr.empty: continue
            r = rr.iloc[0]
            fig.add_trace(go.Scatter(x=TS, y=[r[k] for k in cols], mode='lines+markers', name=c))
        fig.add_vline(x=0.3, line_width=2, line_dash="dash", line_color="blue")
        fig.add_annotation(x=0.3, y=0.1, text="Casas (0,3s)", textangle=-90, font=dict(color="blue", size=10))
        fig.add_vline(x=1.0, line_width=2, line_dash="dash", line_color="orange")
        fig.add_annotation(x=1.0, y=0.1, text="Edificios Medios (1,0s)", textangle=-90, font=dict(color="orange", size=10))
        fig.add_vline(x=3.0, line_width=2, line_dash="dash", line_color="red")
        fig.add_annotation(x=3.0, y=0.1, text="Torres (3,0s)", textangle=-90, font=dict(color="red", size=10))
        fig.update_layout(xaxis_type='log', yaxis_type='log', xaxis_title='Período (s)', yaxis_title='Sa (%g)', title='Espectros de respuesta con resonancia estructural')
        chart_cfg(fig); st.plotly_chart(fig, width='stretch')
        
        d_ciu_fmt = d_ciu.sort_values('psa03', ascending=False).copy()
        num_cols = d_ciu_fmt.select_dtypes(include=['float', 'int']).columns
        for col in num_cols:
            d_ciu_fmt[col] = d_ciu_fmt[col].apply(lambda x: fmt(x, 2) if pd.notna(x) else x)
        st.dataframe(d_ciu_fmt, width='stretch')

def sec_secundarias():
    st.title('⛰️ Deslizamientos y licuefacción')
    lectura('<b>Idea clave:</b> el sismo puede desencadenar otros peligros: <b>deslizamientos</b> en laderas empinadas y <b>licuefacción</b> en valles planos y húmedos. Los modelamos con PGA, pendiente (SRTM) y humedad.')
    capa = st.radio('Capa', ['desliz.png', 'liq.png', 'sar.png'], horizontal=True, format_func=lambda x: {'desliz.png': '🟠 Deslizamientos', 'liq.png': '🔵 Licuefacción', 'sar.png': '🛰️ Cambio SAR'}[x])
    if capa == 'desliz.png':
        items = [('#ffffb2', 'Baja'), ('#fd8d3c', 'Media'), ('#bd0026', 'Alta')]; nota = 'Susceptibilidad = PGA × pendiente, calibrada en zona sacudida'
    elif capa == 'liq.png':
        items = [('#deebf7', 'Baja'), ('#6baed6', 'Media'), ('#08519c', 'Alta')]; nota = 'Licuefacción: valles planos y húmedos con sacudida fuerte'
    else:
        items = [('#000000', 'Sin cambio'), ('#ff4500', 'Cambio ≥ 2.5 dB')]; nota = 'Sentinel-1: |log-ratio VH| pre/post'
    mapa_interactivo('Amenaza secundaria', capa=capa, items=items, nota=nota, infra=osm_infra)
    if not d_sec.empty:
        a, b = st.columns(2)
        with a:
            fig = px.bar(d_sec.sort_values('km2_desliz').tail(10), x='km2_desliz', y='ADM1_NAME', orientation='h', title='km² susceptibles a deslizamientos')
            chart_cfg(fig); st.plotly_chart(fig, width='stretch')
        with b:
            fig = px.bar(d_sec.sort_values('km2_liq').tail(10), x='km2_liq', y='ADM1_NAME', orientation='h', title='km² susceptibles a licuefacción')
            chart_cfg(fig); st.plotly_chart(fig, width='stretch')

def sec_validacion():
    st.title('✅ Validación del modelo')
    lectura('<b>Idea clave:</b> comparamos el PGA modelado por el USGS con el PGA registrado por estaciones reales. Si los puntos se acercan a la línea 1:1, el modelo es confiable.')
    if d_est.empty:
        st.info('El catálogo USGS no publica PGA por estación para este evento aún.')
        mapa_interactivo('Intensidad (MMI)', capa='intensity_overlay.png', bb=BINT, items=[(x[1], x[0]) for x in MMI], infra=osm_infra)
    else:
        a, b = st.columns(2)
        with a:
            fig = px.scatter(d_est, x='pga_mod', y='pga_obs', log_x=True, log_y=True, labels={'pga_mod': 'PGA modelado (%g)', 'pga_obs': 'PGA observado (%g)'}, title='Observado vs modelado')
            mx = float(max(d_est.pga_obs.max(), d_est.pga_mod.max())); mn = max(0.01, float(min(d_est.pga_obs.min(), d_est.pga_mod.min())))
            fig.add_trace(go.Scatter(x=[mn, mx], y=[mn, mx], mode='lines', name='1:1', line={'dash': 'dash'}))
            chart_cfg(fig); st.plotly_chart(fig, width='stretch')
        with b:
            fig = px.scatter(d_est, x='dist_km', y='pga_obs', log_y=True, labels={'dist_km': 'Distancia epicentral (km)', 'pga_obs': 'PGA observado (%g)'}, title='Atenuación con distancia')
            fig.add_trace(go.Scatter(x=d_est.dist_km, y=d_est.pga_mod, mode='markers', name='modelado', marker={'symbol': 'x'}))
            chart_cfg(fig); st.plotly_chart(fig, width='stretch')

def sec_hotosm():
    st.title('🗺️ Mapeo Humanitario (HOTOSM)')
    lectura('<b>Respuesta colaborativa:</b> el Humanitarian OpenStreetMap Team (HOTOSM) activó una respuesta de mapeo colaborativo para este evento. Voluntarios de todo el mundo están mapeando infraestructura crítica, caminos y edificios para apoyar las labores de respuesta.')
    st.subheader('Mapa de Respuesta Humanitaria')
    st.caption('Organizado por **OSM Colombia** con apoyo de **UN Mappers Argentina** y **HOT**')
    
    hotosm_iframe = """
    <div style="width:100%; position:relative; padding-bottom:56.25%; height:0; overflow:hidden; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <iframe src="https://umap.hotosm.org/en/map/colombia-m-74-earthquake-10-ago-2026_3482?scaleControl=false&miniMap=false&scrollWheelZoom=false&zoomControl=true&allowEdit=false&moreControl=true&searchControl=false&tilelayersControl=null&embedControl=null&datalayersControl=true&onLoadPanel=none&captionBar=false&captionMenus=true" 
            style="position:absolute; top:0; left:0; width:100%; height:100%; border:0; frameborder=0;">
        </iframe>
    </div>
    """
    components.html(hotosm_iframe, height=500)

    st.markdown('---'); st.subheader('Capas disponibles en el mapa')
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown('<div class="card card-col"><h3>🗺️ Caplas Base</h3><ul class="mini"><li><b>OpenStreetMap:</b> mapa estándar</li><li><b>Positron:</b> estilo minimalista</li><li><b>Humanitarian:</b> estilo HOT</li><li><b>ESRI:</b> imágenes satelitales</li></ul></div>', unsafe_allow_html=True)
    with col2: st.markdown('<div class="card card-suelo"><h3>📊 Datos del Sismo</h3><ul class="mini"><li><b>Epicentro:</b> San José del Palmar</li><li><b>ShakeMap:</b> zonas de intensidad 3.5 a 6.5</li><li><b>AOI:</b> Área de Interés para mapeo</li><li><b>ChatMap:</b> puntos reportados</li></ul></div>', unsafe_allow_html=True)
    with col3: st.markdown('<div class="card card-ven"><h3>🏘️ Poblaciones Cercanas</h3><ul class="mini"><li><b>San José del Palmar:</b> 2.392 hab. (5,9 km)</li><li><b>Ansermanuevo:</b> 12.332 hab. (27,9 km)</li><li><b>Toro:</b> 13.764 hab. (31,4 km)</li><li><b>La Unión:</b> 41.013 hab. (37,9 km)</li><li><b>Pereira:</b> 467.269 hab. (60,7 km)</li></ul></div>', unsafe_allow_html=True)

    st.markdown('---'); st.subheader('¿Qué es ChatMap?')
    st.write('**ChatMap** es una herramienta de HOTOSM que permite a los equipos de respuesta coordinar el mapeo de manera colaborativa. Los voluntarios pueden:')
    col1, col2 = st.columns(2)
    with col1: st.markdown('- Mapear edificios dañados\n- Identificar caminos bloqueados\n- Marcar infraestructura crítica (hospitales, escuelas)\n- Documentar puentes y estructuras vulnerables')
    with col2: st.markdown('- Validar datos existentes en OpenStreetMap\n- Priorizar áreas según ShakeMap\n- Coordinar con equipos de terreno\n- Generar datos abiertos para organizaciones humanitarias')

    st.markdown('---'); st.subheader('Recursos y Enlaces')
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown('<div class="card card-col"><h3>🔗 Mapa Interactivo</h3><p class="mini">Accede al mapa completo de HOTOSM con todas las capas y datos de mapeo colaborativo.</p><a href="https://umap.hotosm.org/en/map/colombia-m-74-earthquake-10-ago-2026_3482" target="_blank" style="color:#2563eb;">Abrir mapa →</a></div>', unsafe_allow_html=True)
    with col2: st.markdown('<div class="card card-ven"><h3>💬 ChatMap</h3><p class="mini">Plataforma de coordinación para mapeadores voluntarios y equipos de respuesta.</p><a href="https://chatmap.hotosm.org/#map/89319bbb-a14a-4dfd-b9a1-c83b8b55785f" target="_blank" style="color:#ea580c;">Abrir ChatMap →</a></div>', unsafe_allow_html=True)
    with col3: st.markdown('<div class="card card-suelo"><h3>📚 Más Información</h3><p class="mini">Documentación completa sobre la activación y cómo participar.</p><a href="https://d.osm.lat/palmar" target="_blank" style="color:#059669;">Ver detalles →</a></div>', unsafe_allow_html=True)

    st.markdown('---')
    with st.expander('¿Qué es HOTOSM y por qué importa?'):
        st.write('**Humanitarian OpenStreetMap Team (HOTOSM)** es una organización sin fines de lucro que coordina el mapeo colaborativo de OpenStreetMap para respuesta humanitaria y desarrollo internacional.\n\n**Después de un desastre:**\n- Los mapas actualizados salvan vidas al permitir que los equipos de rescate naveguen\n- Las organizaciones humanitarias usan estos datos para planificar la distribución de ayuda\n- Los gobiernos locales identifican infraestructura crítica dañada\n\n**Impacto:** Más de 200.000 mapeadores voluntarios en todo el mundo han contribuido a OpenStreetMap, creando el mapa abierto más grande del mundo.')

def sec_aprende():
    st.title('📚 Glosario y conceptos')
    lectura('Esta sección explica, sin tecnicismos, cada término usado en el observatorio.')
    terms = [('Magnitud (Mw)', 'Energía total liberada. Una sola cifra por sismo. Cada unidad = ~32× más energía.'), ('Intensidad (MMI)', 'Cuánto se sintió en un lugar. Va de I a X+ y disminuye con la distancia.'), ('PGA', 'Aceleración máxima del suelo (% de la gravedad). Mide la "fuerza" del temblor.'), ('PSA', 'Aceleración espectral en un período. Indica qué tipo de edificio resuena más.'), ('Exposición', 'Personas o infraestructura en zonas sacudidas. No implica daño.'), ('Susceptibilidad', 'Probabilidad relativa de que una ladera falle por el sismo.'), ('Licuefacción', 'Pérdida de resistencia del suelo saturado por la sacudida.'), ('Doblete sísmico', 'Dos sismos grandes sucesivos: el segundo golpea estructuras ya degradadas por el primero.'), ('Compatibilidad espectral', 'Cuando el suelo amplifica periodos cercanos al periodo natural de una estructura, el daño aumenta.')]
    for t, d in terms:
        with st.expander(t): st.write(d)

def sec_metodologia():
    st.title('🔬 Metodología, fuentes y límites')
    texto = ("**Autor:** Rafael Leonardo Ruiz Díaz. Ensayo de divulgación para entender el sismo.\n\n**Fuentes:** USGS ShakeMap us6000tjl2 · WorldPop 2020 · ESA WorldCover · VIIRS · SRTM · CHIRPS · Sentinel-1 · FAO GAUL · OpenStreetMap (HOT).\n\n**Método:** exposición = ShakeMap MMI × población a escala nativa (100 m); deslizamientos = PGA × pendiente; licuefacción = PGA × (1−pendiente) × humedad; calibrado dentro de la zona sacudida (MMI ≥ 5).\n\n**Infraestructura crítica:** descargada en tiempo real desde la API de Overpass (OpenStreetMap) para análisis de impacto hospitalario y educativo.\n\n**Comparativa regional:** el análisis Colombia–Venezuela sigue el marco Amenaza × Exposición × Vulnerabilidad.\n\n**Limitaciones:** productos modelados; el raster MMI cubre el núcleo de sacudida; réplicas simuladas si la API no publica.")
    st.markdown(texto)
    st.markdown('---'); st.subheader('Estado de los archivos de datos')
    rows = []
    if os.path.exists(D):
        for f in sorted(os.listdir(D)):
            rows.append({'archivo': f, 'KB': round(os.path.getsize(f'{D}/{f}') / 1024, 1)})
        df_archivos = pd.DataFrame(rows)
        df_archivos['KB'] = df_archivos['KB'].apply(lambda x: fmt(x, 1))
        st.dataframe(df_archivos, width='stretch')
    st.subheader('Descarga de datos')
    if os.path.exists(D):
        for f in sorted(os.listdir(D)):
            if f.endswith('.csv'):
                try: st.download_button(f, open(f'{D}/{f}', 'rb').read(), file_name=f, key=f)
                except: pass

# =====================================================================
# NAVEGACIÓN DE LA APP
# =====================================================================
st.sidebar.title('🌋 Observatorio')
st.sidebar.caption('Sismo M7.4 · Colombia')
SECCIONES = ['🏠 Inicio', '🌍 El sismo', '🧊 Modelo 3D', '🆚 Colombia vs Venezuela', '🎯 Intensidad (MMI)', '👥 Población expuesta', '🏗️ Edificaciones', '⛰️ Amenazas secundarias', '✅ Validación', '🗺️ Mapeo Humanitario', '📚 Aprende', '🔬 Metodología y datos']
op = st.sidebar.radio('Secciones', SECCIONES)
st.sidebar.markdown('---')
st.sidebar.caption('Ensayo: **Rafael Leonardo Ruiz Díaz** · un aporte para entender el sismo')

RUTAS = {
  '🏠 Inicio': sec_inicio, '🌍 El sismo': sec_sismo, '🧊 Modelo 3D': sec_3d, '🆚 Colombia vs Venezuela': sec_comparativa,
  '🎯 Intensidad (MMI)': sec_intensidad, '👥 Población expuesta': sec_poblacion, '🏗️ Edificaciones': sec_edificaciones,
  '⛰️ Amenazas secundarias': sec_secundarias, '✅ Validación': sec_validacion, '🗺️ Mapeo Humanitario': sec_hotosm,
  '📚 Aprende': sec_aprende, '🔬 Metodología y datos': sec_metodologia}
RUTAS[op]()
