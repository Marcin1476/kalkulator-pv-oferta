import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(page_title="Ekspert PV Pro 2026", layout="wide")

# --- INICJALIZACJA SESJI ---
if 'lat' not in st.session_state: st.session_state.lat = 52.23
if 'lon' not in st.session_state: st.session_state.lon = 21.01
if 'city' not in st.session_state: st.session_state.city = "Warszawa"

# --- BAZA DANYCH ---
PANELS = {"Longi 450W": 0.45, "Jinko 550W": 0.55, "Trina 400W": 0.40}
INVERTERS = {
    "Huawei SUN2000": [0.98, 4500],
    "Fronius Symo": [0.97, 6200],
    "SMA Sunny Tripower": [0.98, 7500]
}
BATTERIES = {"Brak": 0, "5 kWh": 5, "10 kWh": 10, "15 kWh": 15}

def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        res = requests.get(url, headers={'User-Agent': 'PV_Pro_V10'}).json()
        if res: return float(res[0]['lat']), float(res[0]['lon']), res[0]['display_name'].split(',')[0]
    except: return None

@st.cache_data
def get_weather_data(lat, lon):
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2025-01-01&end_date=2025-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad_total = sum([r for r in res['daily']['shortwave_radiation_sum'] if r is not None]) / 3.6
        sunny_days = len([r for r in res['daily']['shortwave_radiation_sum'] if r is not None and r > 15])
        return rad_total, sunny_days
    except: return 1050.0, 185

# --- SIDEBAR ---
st.sidebar.header("📍 1. Lokalizacja")
city_in = st.sidebar.text_input("Miasto:", value=st.session_state.city)
if st.sidebar.button("Zaktualizuj"):
    res = get_coords(city_in)
    if res:
        st.session_state.lat, st.session_state.lon, st.session_state.city = res
        st.rerun()

st.sidebar.header("🏗️ 2. Sprzęt")
sel_p = st.sidebar.selectbox("Panel:", list(PANELS.keys()))
num_p = st.sidebar.slider("Liczba paneli:", 1, 60, 14)
sel_inv = st.sidebar.selectbox("Inwerter:", list(INVERTERS.keys()))
sel_b = st.sidebar.selectbox("Magazyn:", list(BATTERIES.keys()))

st.sidebar.header("🔥 3. Pompa Ciepła")
has_hp = st.sidebar.checkbox("Dodaj Pompę Ciepła")
hp_usage = st.sidebar.number_input("Roczne zużycie pompy (kWh):", 0, 10000, 3500) if has_hp else 0

st.sidebar.header("💰 4. Finanse")
bill = st.sidebar.number_input("Rachunek mies. (zł):", 50, 2000, 400)
price = st.sidebar.number_input("Cena 1 kWh (zł):", 0.5, 3.0, 1.25)
cost_kwp = st.sidebar.number_input("Osprzęt i montaż (zł/kWp):", 0, 10000, 4000)

# --- OBLICZENIA ---
rad_total, sunny_days = get_weather_data(st.session_state.lat, st.session_state.lon)
total_kwp = num_p * PANELS[sel_p]
prod_year = total_kwp * rad_total * INVERTERS[sel_inv][0] * 0.9
inv_cost = (total_kwp * cost_kwp) + INVERTERS[sel_inv][1] + (BATTERIES[sel_b] * 2200)

total_usage = ((bill / price) * 12) + hp_usage
autocons_val = 0.3 + (BATTERIES[sel_b] / 25) if BATTERIES[sel_b] > 0 else 0.3
autocons = min(0.8, autocons_val + (0.1 if has_hp else 0)) # Pompa zwiększa autokonsumpcję

savings = (prod_year * autocons * price) + (prod_year * (1 - autocons) * 0.50)
roi = inv_cost / savings if savings > 0 else 0

# --- WIDOK ---
st.title(f"☀️ System Hybrydowy: {st.session_state.city}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Słoneczne Dni", f"{sunny_days}")
c2.metric("Moc PV", f"{round(total_kwp, 2)} kWp")
c3.metric("Koszt", f"{int(inv_cost)} zł")
c4.metric("Zwrot", f"{round(roi, 1)} lat")

st.divider()

col_a, col_b = st.columns([1, 1])
with col_a:
    st.subheader("📍 Lokalizacja")
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=12)
    folium.Marker([st
