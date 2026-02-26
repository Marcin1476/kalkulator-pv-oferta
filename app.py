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
tilt = st.sidebar.slider("Kąt nachylenia (°)", 0, 90, 35)
orient = st.sidebar.selectbox("Orientacja", ["Południe", "Wschód-Zachód", "Inna"])

# Korekty
az_map = {"Południe": 1.0, "Wschód-Zachód": 0.85, "Inna": 0.75}
tilt_corr = 1.0 if 20 <= tilt <= 45 else 0.9

st.sidebar.header("💰 3. Finanse i Sprzęt")
bill = st.sidebar.number_input("Rachunek miesięczny (zł):", 50, 2000, 400)
price = st.sidebar.number_input("Cena 1 kWh (zł):", 0.5, 3.0, 1.25)
cost_kwp = st.sidebar.number_input("Koszt 1 kWp (zł):", 3000, 7000, 4500)

P_DB = {"Longi 450W": 0.45, "Jinko 550W": 0.55, "Trina 400W": 0.40}
sel_p = st.sidebar.selectbox("Model panela:", list(P_DB.keys()))
num_p = st.sidebar.slider("Liczba paneli:", 1, 60, 14)

B_DB = {"Brak": 0, "5 kWh": 5, "10 kWh": 10, "15 kWh": 15}
sel_b = st.sidebar.selectbox("Magazyn energii:", list(B_DB.keys()))

# --- OBLICZENIA (NAPRAWIONA LINIA 69) ---
rad = get_sun_data(st.session_state.lat, st.session_state.lon)
total_kwp = num_p * P_DB[sel_p]
prod_year = total_kwp * (rad * 0.85) * az_map[orient] * tilt_corr
inv_cost = (total_kwp * cost_kwp) + (B_DB[sel_b] * 2200)

# Obliczanie autokonsumpcji
autocons_val = 0.3 + (B_DB[sel_b] / 25) if B_DB[sel_b] > 0 else 0.3
autocons = min(0.75, autocons_val)

savings = (prod_year * autocons * price) + (prod_year * (1 - autocons) * 0.50)
roi = inv_cost / savings if savings > 0 else 0

# --- WIDOK GŁÓWNY ---
st.title(f"☀️ Raport Ekspercki PV: {st.session_state.city}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Moc", f"{round(total_kwp, 2)} kWp")
c2.metric("Inwestycja", f"{int(inv_cost)} zł")
c3.metric("Zysk roczny", f"{int(savings)} zł")
c4.metric("Zwrot", f"{round(roi, 1)} lat")

st.divider()

col_map, col_plots = st.columns([1, 1])

with col_map:
    st.subheader("📍 Mapa i Dane")
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=12)
    folium.Marker([st.session_state.lat, st.session_state.lon]).add_to(m)
    st_folium(m, height=250, use_container_width=True, key="map_v7")
    st.write(f"Produkcja: {int(prod_year)} kWh/rok")
    st.write(f"Autokonsumpcja: {int(autocons*100)}%")

with col_plots:
    st.subheader("📈 Wykres Cash Flow")
    years = np.arange(0, 16)
    cash_flow = [-inv_cost + (y * savings) for y in years]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(years, cash_flow, marker='o', color='#27ae60', lw=2)
    ax.axhline(0, color='red', lw=1, ls='--')
    ax.set_xlabel("Lata")
    ax.set_ylabel("Bilans (zł)")
    st.pyplot(fig)

# --- WIZUALIZACJA ---
st.subheader("🖼️ Projekt rozmieszczenia")
cols = 8
rows = -(-num_p // cols)
fig_pv, ax_pv = plt.subplots(figsize=(10, 3))
for i in range(num_p):
    r, c = divmod(i, cols)
    ax_pv.add_patch(patches.Rectangle((c*1.3, r*2.2), 1.2, 2.0, color='#1a237e', ec='white'))
ax_pv.set_xlim(-0.5, cols * 1.5)
ax_pv.set_ylim(-0.5, rows * 2.5)
plt.axis('off')
st.pyplot(fig_pv)

# --- PDF ---
if st.button("📥 Pobierz PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "OFERTA FOTOWOLTAICZNA 2025", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Lokalizacja: {st.session_state.city}", ln=True)
    pdf.cell(200, 10, f"Moc: {round(total_kwp, 2)} kWp", ln=True)
    pdf.cell(200, 10, f"Czas zwrotu: {round(roi, 1)} lat", ln=True)
    res_pdf = pdf.output(dest='S').encode('latin-1')
    st.download_button("Zapisz Raport PDF", res_pdf, "Oferta_PV.pdf")
