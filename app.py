import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Ekspert PV Pro 2025", layout="wide")

# --- KONFIGURACJA ---
PANELS_DB = {"Longi 450W": 0.45, "Jinko 550W": 0.55, "Trina 400W": 0.40}
BATTERY_DB = {"Brak": 0, "5 kWh": 5, "10 kWh": 10, "15 kWh": 15}

def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'Kalkulator_PV_App_V5'}
        res = requests.get(url, headers=headers).json()
        if res: return float(res[0]['lat']), float(res[0]['lon']), res[0]['display_name'].split(',')[0]
    except: return None

@st.cache_data
def get_weather_2025(lat, lon):
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2025-01-01&end_date=2025-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad_list = res['daily']['shortwave_radiation_sum']
        total_rad_kwh = sum([r for r in rad_list if r is not None]) / 3.6
        return total_rad_kwh
    except: return 1050.0

if 'lat' not in st.session_state:
    st.session_state.lat, st.session_state.lon, st.session_state.city_name = 52.23, 21.01, "Warszawa"

# --- SIDEBAR ---
st.sidebar.header("📍 1. Lokalizacja")
city_input = st.sidebar.text_input("Wpisz miasto:", st.session_state.city_name)
if st.sidebar.button("Zastosuj"):
    res = get_coords(city_input)
    if res:
        st.session_state.lat, st.session_state.lon, st.session_state.city_name = res
        st.rerun()

st.sidebar.header("💰 2. Parametry")
monthly_bill = st.sidebar.number_input("Rachunek miesięczny (zł):", 50, 2000, 400)
energy_price = st.sidebar.number_input("Cena 1 kWh (zł):", 0.5, 3.0, 1.25)
installation_cost_per_kwp = st.sidebar.number_input("Koszt 1 kWp (zł):", 3000, 7000, 4500)

st.sidebar.header("🏗️ 3. Sprzęt")
sel_panel = st.sidebar.selectbox("Model panela:", list(PANELS_DB.keys()))
num_panels = st.sidebar.slider("Liczba paneli:", 1, 60, 14)
sel_battery = st.sidebar.selectbox("Magazyn energii:", list(BATTERY_DB.keys()))

# --- OBLICZENIA ---
rad_m2 = get_weather_2025(st.session_state.lat, st.session_state.lon)
total_kwp = num_panels * PANELS_DB[sel_panel]
production_kwh = total_kwp * (rad_m2 * 0.85)
annual_usage_kwh = (monthly_bill / energy_price) * 12

# Koszty i zwrot
total_cost = (total_kwp * installation_cost_per_kwp) + (BATTERY_DB[sel_battery] * 2000)
autocons = 0.3 + (BATTERY_DB[sel_battery] / 25) if BATTERY_DB[sel_battery] > 0 else 0.3
autocons = min(0.75, autocons)
annual_savings = (production_kwh * autocons * energy_price) + (production_kwh * (1 - autocons) * 0.50)
years_to_return = total_cost / annual_savings if annual_savings > 0 else 0

# --- INTERFEJS ---
st.title(f"☀️ Raport Inwestycyjny PV 2025: {st.session_state.city_name}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Moc Instalacji", f"{round(total_kwp, 2)} kWp")
c2.metric("Koszt Całkowity", f"{int(total_cost)} zł")
c3.metric("Roczny Zysk", f"{int(annual_savings)} zł")
c4.metric("Czas Zwrotu", f"{round(years
