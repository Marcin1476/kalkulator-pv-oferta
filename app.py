import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(page_title="Ekspert PV Pro 2026", layout="wide")

# --- START SESJI ---
if 'lat' not in st.session_state: st.session_state.lat = 52.23
if 'lon' not in st.session_state: st.session_state.lon = 21.01
if 'city' not in st.session_state: st.session_state.city = "Warszawa"

# --- BAZA ---
PANELS = {"Longi 450W": 0.45, "Jinko 550W": 0.55, "Trina 400W": 0.40}
INV_DB = {"Huawei": [0.98, 4500], "Fronius": [0.97, 6200], "SMA": [0.98, 7500]}
BAT_DB = {"Brak": 0, "5 kWh": 5, "10 kWh": 10, "15 kWh": 15}

def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        r = requests.get(url, headers={'User-Agent': 'PV_App_2026'}).json()
        if r: return float(r[0]['lat']), float(r[0]['lon']), r[0]['display_name'].split(',')[0]
    except: return None

@st.cache_data
def get_sun(lat, lon):
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2025-01-01&end_date=2025-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad = sum([r for r in res['daily']['shortwave_radiation_sum'] if r is not None]) / 3.6
        sunny = len([r for r in res['daily']['shortwave_radiation_sum'] if r is not None and r > 15])
        return rad, sunny
    except: return 1050.0, 185

# --- MENU BOCZNE ---
st.sidebar.header("📍 1. Lokalizacja")
c_in = st.sidebar.text_input("Miasto:", value=st.session_state.city)
if st.sidebar.button("Zastosuj"):
    res = get_coords(c_in)
    if res:
        st.session_state.lat, st.session_state.lon, st.session_state.city = res
        st.rerun()

st.sidebar.header("🏗️ 2. Sprzęt")
s_p = st.sidebar.selectbox("Panel:", list(PANELS.keys()))
n_p = st.sidebar.slider("Ilość paneli:", 1, 60, 14)
s_i = st.sidebar.selectbox("Inwerter:", list(INV_DB.keys()))
s_b = st.sidebar.selectbox("Magazyn:", list(BAT_DB.keys()))

st.sidebar.header("💰 3. Finanse")
m_cost = st.sidebar.number_input("Montaż/Osprzęt (zł/kWp):", 0, 10000, 4000)

# --- LOGIKA ---
rad, sunny = get_sun(st.session_state.lat, st.session_state.lon)
kwp = n_p * PANELS[s_p]
eff, i_prc = INV_DB[s_i]
prod = kwp * rad * eff * 0.9
total_inv = (kwp * m_cost) + i_prc + (BAT_DB[s_b] * 2200)

# --- WIDOK ---
st.title(f"☀️ Analiza Techniczna: {st.session_state.city}")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Dni Słoneczne", sunny)
k2.metric("Moc Układu", f"{round(kwp,2)} kWp")
k3.metric("Energia Rok 1", f"{int(prod)} kWh")
k4.metric("Koszt Zestawu", f"{int(total_inv)} zł")

st.divider()

m_col, g_col = st.columns([1, 1])
with m_col:
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=12)
    folium.Marker([st.session_state.lat, st.session_state.lon]).add_to(m)
    st_folium(m, height=250, use_container_width=True, key="map_v11")

with g_col:
    st.subheader("📉 Wydajność paneli w czasie (25 lat)")
    years = np.arange(1, 26)
    efficiency = [100 - (y * 0.5) for y in years]
    
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(years, efficiency, color='#e67e22', lw=3)
    ax.fill_between(years, efficiency, 80, color='#f39c12', alpha=0.2)
    ax.set_ylim(80, 105)
    ax.set_xlabel("Lata")
    ax.set_ylabel("Wydajność (%)")
    ax.grid(True, linestyle='--', alpha=0.6)
    st.pyplot(fig)

st.subheader("Wizualizacja Rozmieszczenia")
c_n = 8
r_n = -(-n_p // c_n)
fig_pv, ax_pv = plt.subplots(figsize=(10, 3))
for i in range(n_p):
    r, c = divmod(i, c_n)
    ax_pv.add_patch(patches.Rectangle((c*1.3, r*2.2), 1.2, 2.0, color='#1a237e', ec='white'))
ax_pv.set_xlim(-0.5, 12)
ax_pv.set_ylim(-0.5, r_n * 2.5)
plt.axis('off')
st.pyplot(fig_pv)

if st.button("📥 Generuj Raport PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "RAPORT TECHNICZNY PV 2026", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Lokalizacja: {st.session_state.city}", ln=True)
    pdf.cell(200, 10, f"Dni sloneczne: {sunny}", ln=True)
    pdf.cell(200, 10, f"Moc poczatkowa: {round(kwp,2)} kWp", ln=True)
    res = pdf.
