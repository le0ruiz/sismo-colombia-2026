🌋 Observatorio Sísmico Interactivo: Colombia 2026
Dashboard interactivo de divulgación científica y gestión del riesgo que modela un escenario de sismo M7.4 en Colombia. El proyecto traduce datos técnicos complejos (sismología, ingeniería estructural y geomática) en una herramienta visual para la toma de decisiones y respuesta humanitaria.

🔗 App en vivo: Observatorio Sismo Colombia 2026

🎯 Características Principales
Mapas Interactivos (Leaflet/Folium): Visualización del ShakeMap del USGS con capas activables de infraestructura crítica (hospitales y escuelas) consultadas en tiempo real desde la API de OpenStreetMap (Overpass).
Análisis de Exposición: Cruce de datos de intensidad sísmica (MMI) con población (WorldPop) para estimar personas y áreas urbanas afectadas.
Ingeniería Estructural: Gráficos de espectros de respuesta (PSA) con líneas de resonancia que explican por qué distintos edificios (casas, torres) sufren daños diferenciados.
Amenazas Secundarias: Modelado espacial de susceptibilidad a deslizamientos y licuefacción de suelos.
Mapeo Humanitario (HOTOSM): Integración directa con mapas de activación de OpenStreetMap y ChatMap para coordinación de voluntarios.
Diseño Responsive: Interfaz adaptada para celulares, tablets y pantallas gigantes.
🛠️ Tech Stack (Tecnologías utilizadas)
Lenguaje: Python 3.10+
Framework Web: Streamlit
Geoespacial: Folium, Leaflet, GeoPandas, Shapely
Visualización: Plotly, Matplotlib
Datos: Pandas, NumPy
APIs Externas: USGS ShakeMap, Overpass API (OpenStreetMap)
🚀 Ejecución Local
Si deseas ejecutar este proyecto en tu computadora:

Clona el repositorio:
git clone https://github.com/le0ruiz/sismo-colombia-2026.gitcd sismo-colombia-2026
Crea un entorno virtual e instala las dependencias:
bash

python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
Ejecuta la aplicación:
bash

streamlit run app.py
📚 Metodología y Fuentes
Sismo: Escenario simulado M7.4 (Profundidad ~107 km).
Fuentes de Datos: USGS, WorldPop 2020, ESA WorldCover, VIIRS, SRTM, CHIRPS, Sentinel-1, FAO GAUL, OpenStreetMap.
Método:
Exposición: ShakeMap MMI × población a escala nativa (100 m).
Deslizamientos: PGA × pendiente.
Licuefacción: PGA × (1−pendiente) × humedad.

👤 Autor
Rafael Leonardo Ruiz Díaz

Ensayo de divulgación para entender el sismo. Un aporte para entender que el Riesgo Sísmico = Amenaza × Exposición × Vulnerabilidad.
