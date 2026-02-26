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
    "SMA Sunny Tripower": [0.98, 7500],
    "Growatt MOD": [0.96, 3800]
}
BATTERIES = {"Brak": 0, "5 kWh": 5, "10 kWh": 10, "15 kWh": 15}

# --- FUNKCJE ---
def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        res = requests.get(url, headers={'User-Agent': 'PV_App_2026'}).json()
        if res: return float(res[0]['lat']), float(res[0]['lon']), res[0]['display_name'].split(',')[0]
    except: return None

@st.cache_data
def get_weather_data(lat, lon):
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2025-01-01&end_date=2025-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad_list = res['daily']['shortwave_radiation_sum']
        rad_total = sum([r for r in rad_list if r is not None]) / 3.6
        sunny_days = len([r for r in rad_list if r is not None and r > 15])
        return rad_total, sunny_days
    except: return 1050.0, 185

# --- SIDEBAR ---
st.sidebar.header("📍 1. Lokalizacja")
city_in = st.sidebar.text_input("Miasto:", value=st.session_state.city)
if st.sidebar.button("Zaktualizuj lokalizację"):
    res = get_coords(city_in)
    if res:
        st.session_state.lat, st.session_state.lon, st.session_state.city = res
        st.rerun()

st.sidebar.header("🏗️ 2. Parametry Dachu")
roof_tilt = st.sidebar.slider("Kąt nachylenia dachu (°)", 0, 90, 35)
roof_dir = st.sidebar.selectbox("Kierunek świata", ["Południe", "Południowy-Wschód", "Południowy-Zachód", "Wschód", "Zachód", "Północ"])

# Współczynniki korygujące (uproszczona macierz wydajności)
dir_corr_map = {
    "Południe": 1.0, 
    "Południowy-Wschód": 0.96, 
    "Południowy-Zachód": 0.96, 
    "Wschód": 0.82, 
    "Zachód": 0.82, 
    "Północ": 0.55
}
# Korekta kąta (najlepszy uzysk 30-40 stopni)
tilt_corr = 1.0 - (abs(roof_tilt - 35) * 0.003) 
final_roof_corr = dir_corr_map[roof_dir] * tilt_corr

st.sidebar.header("🏗️ 3. Konfiguracja PV")
sel_p = st.sidebar.selectbox("Model paneli:", list(PANELS.keys()))
num_p = st.sidebar.slider("Liczba paneli:", 1, 60, 14)
sel_inv = st.sidebar.selectbox("Model inwertera:", list(INVERTERS.keys()))
sel_b = st.sidebar.selectbox("Magazyn energii:", list(BATTERIES.keys()))

st.sidebar.header("🔥 4. Zużycie Pompy Ciepła")
hp_consumption = st.sidebar.number_input("Roczne zużycie PC (kWh):", 0, 15000, 4000)

st.sidebar.header("💰 5. Koszty")
bill = st.sidebar.number_input("Rachunek za prąd bytowy (mies.):", 50, 2000, 300)
price = st.sidebar.number_input("Cena 1 kWh (zł):", 0.5, 3.0, 1.25)
cost_kwp = st.sidebar.number_input("Montaż i osprzęt (zł/kWp):", 0, 10000, 4000)

# --- OBLICZENIA ---
rad_total, sunny_days = get_weather_data(st.session_state.lat, st.session_state.lon)
total_kwp = num_p * PANELS[sel_p]
inv_eff = INVERTERS[sel_inv][0]
inv_price = INVERTERS[sel_inv][1]

# Produkcja z uwzględnieniem lokalizacji, sprzętu oraz parametrów dachu
prod_year = total_kwp * rad_total * inv_eff * final_roof_corr * 0.9
total_investment = (total_kwp * cost_kwp) + inv_price + (BATTERIES[sel_b] * 2000)

base_ac = 0.25 + (BATTERIES[sel_b] / 25)
if hp_consumption > 0:
    base_ac += 0.20
autocons = min(0.85, base_ac)

savings = (prod_year * autocons * price) + (prod_year * (1 - autocons) * 0.50)
roi = total_investment / savings if savings > 0 else 0

# --- WIDOK GŁÓWNY ---
st.title(f"☀️ Raport Techniczny PV 2026: {st.session_state.city}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Dni Słoneczne", f"{sunny_days}")
c2.metric("Moc Układu", f"{round(total_kwp, 2)} kWp")
c3.metric("Wydajność Dachu", f"{int(final_roof_corr*100)}%")
c4.metric("Czas Zwrotu", f"{round(roi, 1)} lat")

st.divider()

col_map, col_plots = st.columns([1, 1])

with col_map:
    st.subheader("📍 Dane i Lokalizacja")
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=12)
    folium.Marker([st.session_state.lat, st.session_state.lon]).add_to(m)
    st_folium(m, height=250, use_container_width=True, key="map_v11")
    st.info(f"Parametry dachu: **{roof_dir}**, kąt **{roof_tilt}°**. Nasłonecznienie: **{int(rad_total)} kWh/m²**")

with col_plots:
    st.subheader("📉 Efektywność paneli w czasie (25 lat)")
    years_25 = np.arange(1, 26)
    efficiency = [100 - (y * 0.5) for y in years_25]
    fig_eff, ax_eff = plt.subplots(figsize=(6, 4))
    ax_eff.plot(years_25, efficiency, color='#e67e22', lw=3)
    ax_eff.fill_between(years_25, efficiency, 80, color='#f39c12', alpha=0.2)
    ax_eff.set_ylim(80, 105)
    ax_eff.set_ylabel("Wydajność (%)")
    st.pyplot(fig_eff)



st.subheader("🖼️ Projekt Rozmieszczenia Paneli")
cols = 8
rows = -(-num_p // cols)
fig_pv, ax_pv = plt.subplots(figsize=(10, 3))
for i in range(num_p):
    r, c = divmod(i, cols)
    ax_pv.add_patch(patches.Rectangle((c*1.3, r*2.2), 1.2, 2.0, color='#1a237e', ec='white'))
ax_pv.set_xlim(-0.5, 12)
ax_pv.set_ylim(-0.5, rows * 2.5)
plt.axis('off')
st.pyplot(fig_pv)

if st.button("📥 Pobierz PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "ANALIZA TECHNICZNA PV 2026", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Lokalizacja: {st.session_state.city} ({sunny_days} dni slonecznych)", ln=True)
    pdf.cell(200, 10, f"Parametry dachu: {roof_dir}, Kat {roof_tilt} deg", ln=True)
    pdf.cell(200, 10, f"Wydajnosc konstrukcyjna: {int(final_roof_corr*100)}%", ln=True)
    pdf.cell(200, 10, f"Moc: {round(total_kwp, 2)} kWp | Zwrot: {round(roi, 1)} lat", ln=True)
    res_pdf = pdf.output(dest='S').encode('latin-1')
    st.download_button("Zapisz Raport PDF", res_pdf, "Raport_PV_Prosument.pdf")
