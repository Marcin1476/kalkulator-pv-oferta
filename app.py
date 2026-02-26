import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(page_title="Ekspert PV Pro - Realistyczna Wizualizacja", layout="wide")

PANELS_DB = {"Longi 450W Black": 0.45, "Jinko 550W Tiger": 0.55, "Trina 400W Vertex": 0.40}
BATTERY_DB = {"Brak": 0, "5 kWh": 5, "10 kWh": 10, "15 kWh": 15}

def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'PV_Pro_Real_Vis'}
        res = requests.get(url, headers=headers).json()
        if res: return float(res[0]['lat']), float(res[0]['lon']), res[0]['display_name'].split(',')[0]
    except: return None

@st.cache_data
def get_weather_2025(lat, lon):
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2025-01-01&end_date=2025-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad_list = res['daily']['shortwave_radiation_sum']
        sunny_days = len([r for r in rad_list if r is not None and r > 18])
        total_rad_kwh = sum([r for r in rad_list if r is not None]) / 3.6
        return total_rad_kwh, sunny_days
    except: return 1050.0, 190

if 'lat' not in st.session_state:
    st.session_state.lat, st.session_state.lon, st.session_state.city_name = 52.22, 21.01, "Warszawa"

# --- SIDEBAR ---
st.sidebar.header("📍 Lokalizacja")
city_q = st.sidebar.text_input("Miasto:", st.session_state.city_name)
if st.sidebar.button("Zmień lokalizację"):
    res = get_coords(city_q)
    if res: 
        st.session_state.lat, st.session_state.lon, st.session_state.city_name = res
        st.rerun()

st.sidebar.header("💰 Dane Finansowe")
monthly_bill = st.sidebar.number_input("Rachunek miesięczny (zł):", 50, 2000, 400)
energy_price = st.sidebar.number_input("Cena prądu (zł/kWh):", 0.5, 3.0, 1.20)

st.sidebar.header("🏗️ Konfiguracja Systemu")
sel_panel = st.sidebar.selectbox("Model panela:", list(PANELS_DB.keys()))
num_panels = st.sidebar.slider("Liczba paneli:", 1, 40, 12)
sel_battery = st.sidebar.selectbox("Magazyn energii:", list(BATTERY_DB.keys()))

# --- OBLICZENIA ---
rad_m2, sunny_days = get_weather_2025(st.session_state.lat, st.session_state.lon)
total_kwp = num_panels * PANELS_DB[sel_panel]
production = total_kwp * (rad_m2 * 0.85)
annual_usage_kwh = (monthly_bill / energy_price) * 12

# Logika zysku
autocons_base = 0.3
battery_cap = BATTERY_DB[sel_battery]
autocons_total = min(0.75, autocons_base + (battery_cap / 20))
annual_savings = (production * autocons_total * energy_price) + (production * (1 - autocons_total) * 0.50)

# --- INTERFEJS ---
st.title(f"☀️ Raport Fotowoltaiczny 2025: {st.session_state.city_name}")

c1, c2, c3 = st.columns(3)
c1.metric("Zużycie roczne", f"{int(annual_usage_kwh)} kWh")
c2.metric("Produkcja z PV", f"{int(production)} kWh")
c3.metric("Oszczędność", f"{int(annual_savings)} zł/rok")

st.divider()

# --- REALISTYCZNA WIZUALIZACJA ---
st.subheader("🖼️ Realistyczna wizualizacja na połaci dachowej")

def draw_realistic_pv(n):
    cols = 6 if n > 6 else n
    rows = -(-n // cols)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    # Tło jako dach (dachówka)
    ax.set_facecolor('#34495e') 
    
    for i in range(n):
        r, c = divmod(i, cols)
        x, y = c * 1.3, r * 2.2
        
        # Ramka panela (szary aluminium)
        ax.add_patch(patches.Rectangle((x, y), 1.2, 2.0, color='#2c3e50', zorder=1))
        # Główne szkło panela (ciemny granat/czarny)
        ax.add_patch(patches.Rectangle((x+0.05, y+0.05), 1.1, 1.9, color='#1a1a2e', zorder
