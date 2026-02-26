import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium
import io

st.set_page_config(page_title="Ekspert PV Pro - Lokalizator", layout="wide")

# --- BAZA DANYCH ---
PANELS_DB = {"Longi 450W": {"power": 0.45, "w": 1.13, "h": 1.76}, "Jinko 550W": {"power": 0.55, "w": 1.13, "h": 2.27}}
ROOF_TYPES = {"Blachodachówka": 250, "Dachówka": 450, "Dach Płaski": 550, "Grunt": 800}

# --- FUNKCJA SZUKANIA MIASTA ---
def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?city={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'PV_App_User'}
        res = requests.get(url, headers=headers).json()
        if res:
            return float(res[0]['lat']), float(res[0]['lon'])
    except: return None
    return None

# --- SIDEBAR ---
st.sidebar.header("📍 Lokalizacja Instalacji")
city_input = st.sidebar.text_input("Wpisz miejscowość:", "Warszawa")
search_btn = st.sidebar.button("Znajdź na mapie")

st.sidebar.header("🏗️ Parametry Systemu")
sel_panel = st.sidebar.selectbox("Model Panela", list(PANELS_DB.keys()))
num_panels = st.sidebar.slider("Liczba paneli", 1, 60, 12)
energy_price = st.sidebar.number_input("Cena prądu (zł/kWh)", 0.0, 3.0, 1.15)

# --- LOGIKA LOKALIZACJI ---
if 'lat' not in st.session_state:
    st.session_state.lat, st.session_state.lon = 52.23, 21.01

if search_btn:
    coords = get_coords(city_input)
    if coords:
        st.session_state.lat, st.session_state.lon = coords
    else:
        st.error("Nie znaleziono miejscowości. Spróbuj ponownie.")

# --- POBIERANIE DANYCH POGODOWYCH ---
@st.cache_data
def get_weather(lat, lon):
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2024-01-01&end_date=2024-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad_list = res['daily']['shortwave_radiation_sum']
        sunny_days = len([r for r in rad_list if r > 18]) # Próg nasłonecznienia dla dnia "bardzo słonecznego"
        return sum(rad_list) / 3.6, sunny_days
    except: return 1000.0, 185

rad, sunny_days = get_weather(st.session_state.lat, st.session_state.lon)
total_pwr = num_panels * PANELS_DB[sel_panel]["power"]
yield_kwh = total_pwr * (rad / 1000) * 0.85

# --- INTERFEJS GŁÓWNY ---
st.title(f"☀️ Analiza PV dla miejscowości: {city_input}")
st.markdown(f"**Współrzędne:** {round(st.session_state.lat, 4)}, {round(st.session_state.lon, 4)}")

c_map, c_stats = st.columns([2, 1])

with c_map:
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=12)
    folium.Marker([st.session_state.lat, st.session_state.lon], popup=city_input).add_to(m)
    st_folium(m, height=400, use_container_width=True, key="map")

with c_stats:
    st.metric("Dni słoneczne (2024)", f"{sunny_days} dni")
    st.metric("Roczny uzysk energii", f"{int(yield_kwh)} kWh")
    st.metric("Oszczędność roczna", f"{int(yield_kwh * energy_price)} zł")
    st.info("Dane nasłonecznienia pobrane automatycznie dla wybranej pozycji.")

# --- WIZUALIZACJA ---
st.subheader("🖼️ Projekt rozmieszczenia paneli")
cols_ui = 6
rows_ui = -(-num_panels // cols_ui)
fig, ax = plt.subplots(figsize=(10, 3))
ax.set_facecolor('#ecf0f1')
for i in range(num_panels):
    r, c = divmod(i, cols_ui)
    ax.add_patch(patches.Rectangle((c * 1.2, r * 1.9), 1.1, 1.8, color='#2c3e50', ec='white'))
plt.axis('off')
st.pyplot(fig)

# --- EKSPORT PDF ---
if st.button("📥 Pobierz Ofertę z Danymi Lokalnymi"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"OFERTA DLA MIEJSCOWOSCI: {city_input.upper()}", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Lokalizacja: {city_input} (Lat: {round(st.session_state.lat,2)}, Lon: {round(st.session_state.lon,2)})", ln=True)
    pdf.cell(200, 10, f"Liczba dni slonecznych: {sunny_days}", ln=True)
    pdf.cell(200, 10, f"Moc instalacji: {round(total_pwr, 2)} kWp", ln=True)
    pdf.cell(200, 10, f"Zysk roczny przy cenie {energy_price} zl/kWh: {int(yield_kwh * energy_price)} zl", ln=True)
    
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    st.download_button(label="Pobierz PDF", data=pdf_bytes, file_name=f"Oferta_{city_input}.pdf", mime="application/pdf")
