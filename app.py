import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Ekspert PV Pro 2025", layout="wide")

def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'Kalkulator_PV_2025'}
        response = requests.get(url, headers=headers).json()
        if response:
            return float(response[0]['lat']), float(response[0]['lon']), response[0]['display_name'].split(',')[0]
    except:
        return None
    return None

@st.cache_data
def get_weather_2025(lat, lon):
    try:
        # Pobieramy dane za cały rok 2025
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2025-01-01&end_date=2025-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad_list = res['daily']['shortwave_radiation_sum']
        
        # Filtracja dni słonecznych (nasłonecznienie > 18 MJ/m2)
        sunny_days = len([r for r in rad_list if r is not None and r > 18])
        total_rad_kwh = sum([r for r in rad_list if r is not None]) / 3.6
        return total_rad_kwh, sunny_days
    except:
        return 1050.0, 190

# --- SESJA I LOKALIZACJA ---
if 'lat' not in st.session_state:
    st.session_state.lat, st.session_state.lon = 52.2297, 21.0122
    st.session_state.city_name = "Warszawa"

# --- SIDEBAR ---
st.sidebar.header("📍 Lokalizacja (Dane 2025)")
city_query = st.sidebar.text_input("Wpisz miasto:", st.session_state.city_name)

if st.sidebar.button("Zastosuj i przelicz dla 2025"):
    res = get_coords(city_query)
    if res:
        st.session_state.lat, st.session_state.lon, st.session_state.city_name = res
        st.rerun()
    else:
        st.sidebar.error("Nie znaleziono miejscowości.")

st.sidebar.header("🏗️ Parametry")
num_panels = st.sidebar.slider("Liczba paneli:", 1, 80, 14)
energy_price = st.sidebar.number_input("Cena energii (zł/kWh):", 0.0, 3.5, 1.25)

# --- OBLICZENIA ---
rad_2025, sunny_days_2025 = get_weather_2025(st.session_state.lat, st.session_state.lon)
total_kwp = num_panels * 0.45
production = total_kwp * (rad_2025 / 1000) * 0.85
annual_profit = production * energy_price

# --- INTERFEJS ---
st.title(f"☀️ Raport Nasłonecznienia 2025: {st.session_state.city_name}")

c1, c2 = st.columns([2, 1])

with c1:
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=11)
    folium.Marker([st.session_state.lat, st.session_state.lon], popup=st.session_state.city_name).add_to(m)
    st_folium(m, height=400, use_container_width=True, key="map_2025")

with c2:
    st.subheader("Statystyki za rok 2025")
    st.metric("Dni słoneczne", f"{sunny_days_2025} dni")
    st.metric("Suma energii", f"{int(rad_2025)} kWh/m²")
    st.metric("Moc systemu", f"{round(total_kwp, 2)} kWp")
    st.success(f"Zysk: {int(annual_profit)} zł/rok")

st.divider()

# --- WIZUALIZACJA ---
st.subheader("🖼️ Rozmieszczenie paneli na dachu")
cols = 7 if num_panels > 7 else num_panels
rows = -(-num_panels // cols)
fig, ax = plt.subplots(figsize=(10, 4))
ax.set_facecolor('#cfd8dc')

for i in range(num_panels):
    r, c = divmod(i, cols)
    ax.add_
