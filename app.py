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

def get_coords(city):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1"
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

st.sidebar.header("🔥 3. Pompa Ciepła")
use_hp = st.sidebar.checkbox("Mam pompę ciepła")
hp_kwh = st.sidebar.number_input("Zużycie pompy (kWh/rok):", 0, 10000, 3500) if use_hp else 0

st.sidebar.header("💰 4. Finanse")
bill = st.sidebar.number_input("Rachunek mies. (zł):", 50, 2000, 400)
prc = st.sidebar.number_input("Cena 1 kWh (zł):", 0.5, 3.0, 1.25)
# Zakres montażu od 0 zł
m_cost = st.sidebar.number_input("Montaż/Osprzęt (zł/kWp):", 0, 10000, 4000)

# --- LOGIKA ---
rad, sunny = get_sun(st.session_state.lat, st.session_state.lon)
kwp = n_p * PANELS[s_p]
eff, i_prc = INV_DB[s_i]
prod = kwp * rad * eff * 0.9
total_inv = (kwp * m_cost) + i_prc + (BAT_DB[s_b] * 2200)

base_ac = 0.3 + (BAT_DB[s_b] / 25) if BAT_DB[s_b] > 0 else 0.3
ac = min(0.8, base_ac + (0.1 if use_hp else 0))
save = (prod * ac * prc) + (prod * (1 - ac) * 0.50)
roi = total_inv / save if save > 0 else 0

# --- WIDOK ---
st.title(f"☀️ Raport Energii: {st.session_state.city}")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Dni Słoneczne", sunny)
k2.metric("Moc Układu", f"{round(kwp,2)} kWp")
k3.metric("Koszt Całkowity", f"{int(total_inv)} zł")
k4.metric("Zwrot", f"{round(roi,1)} lat")

st.divider()

m_col, g_col = st.columns([1, 1])
with m_col:
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=12)
    folium.Marker([st.session_state.lat, st.session_state.lon]).add_to(m)
    st_folium(m, height=250, use_container_width=True, key="map_final_v10")

with g_col:
    st.subheader("Prognoza Cash Flow")
    yrs = np.arange(0, 16)
    c_f = [-total_inv + (y * save) for y in yrs]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(yrs, c_f, marker='o', color='#2c3e50')
    ax.axhline(0, color='red', ls='--')
    st.pyplot(fig)

st.subheader("Wizualizacja Paneli")
c_n, r_n = 8, -(-n_p // 8)
fig_pv, ax_pv = plt.subplots(figsize=(10, 3))
for i in range(n_p):
    r, c = divmod(i, 8)
    ax_pv.add_patch(patches.Rectangle((c*1.3, r*2.2), 1.2, 2.0, color='#1a237e', ec='white'))
ax_pv.set_xlim(-0.5, 12)
ax_pv.set_ylim(-0.5, r_n * 2.5)
plt.axis('off')
st.pyplot(fig_pv)

if st.button("📥 Generuj PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "OFERTA SYSTEMU PV 2026", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Lokalizacja: {st.session_state.city} ({sunny} dni slon.)", ln=True)
    pdf.cell(200, 10, f"Moc: {round(kwp,2)} kWp | Koszt: {int(total_inv)} zl", ln=True)
    pdf.cell(200, 10, f"Szacowany zwrot: {round(roi,1)} lat", ln=True)
    res = pdf.output(dest='S').encode('latin-1')
    st.download_button("Pobierz Plik PDF", res, "Oferta_PV.pdf")
