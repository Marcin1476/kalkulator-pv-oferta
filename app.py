import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(page_title="Ekspert PV Pro 2025", layout="wide")

# --- INICJALIZACJA SESJI ---
if 'lat' not in st.session_state: st.session_state.lat = 52.23
if 'lon' not in st.session_state: st.session_state.lon = 21.01
if 'city' not in st.session_state: st.session_state.city = "Warszawa"

# --- FUNKCJE ---
def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        res = requests.get(url, headers={'User-Agent': 'PV_Pro_V6'}).json()
        if res: return float(res[0]['lat']), float(res[0]['lon']), res[0]['display_name'].split(',')[0]
    except: return None

@st.cache_data
def get_sun_data(lat, lon):
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2025-01-01&end_date=2025-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad = sum([r for r in res['daily']['shortwave_radiation_sum'] if r is not None]) / 3.6
        return rad
    except: return 1050.0

# --- SIDEBAR ---
st.sidebar.header("📍 1. Lokalizacja")
city_in = st.sidebar.text_input("Miasto:", value=st.session_state.city)
if st.sidebar.button("Zastosuj"):
    res = get_coords(city_in)
    if res:
        st.session_state.lat, st.session_state.lon, st.session_state.city = res
        st.rerun()

st.sidebar.header("🏗️ 2. Parametry Dachu")
roof_tilt = st.sidebar.slider("Kąt nachylenia (°)", 0, 90, 35)
roof_azimuth = st.sidebar.selectbox("Orientacja", ["Południe (0°)", "Południowy-Wschód/Zachód", "Wschód/Zachód"])

# Korekta wydajności na podstawie dachu
azimuth_corr = {"Południe (0°)": 1.0, "Południowy-Wschód/Zachód": 0.92, "Wschód/Zachód": 0.82}
tilt_corr = 1.0 if 20 <= roof_tilt <= 45 else 0.9 # Uproszczona korekta kąta

st.sidebar.header("💰 3. Finanse i Sprzęt")
bill = st.sidebar.number_input("Rachunek miesięczny (zł):", 50, 2000, 400)
price = st.sidebar.number_input("Cena 1 kWh (zł):", 0.5, 3.0, 1.25)
cost_per_kwp = st.sidebar.number_input("Koszt 1 kWp (zł):", 3000, 7000, 4500)

PANELS = {"Longi 450W": 0.45, "Jinko 550W": 0.55, "Trina 400W": 0.40}
sel_p = st.sidebar.selectbox("Model panela:", list(PANELS.keys()))
num_p = st.sidebar.slider("Liczba paneli:", 1, 60, 14)

BATTERIES = {"Brak": 0, "5 kWh": 5, "10 kWh": 10, "15 kWh": 15}
sel_b = st.sidebar.selectbox("Magazyn energii:", list(BATTERIES.keys()))

# --- OBLICZENIA ---
rad = get_sun_data(st.session_state.lat, st.session_state.lon)
total_kwp = num_p * PANELS[sel_p]
# Produkcja z uwzględnieniem korekty dachu
prod_year = total_kwp * (rad * 0.85) * azimuth_corr[roof_azimuth] * tilt_corr
inv_cost = (total_kwp * cost_per_kwp) + (BATTERIES[sel_b] * 2000)
autocons = min(0.75, (0.3 + (BATTERIES
