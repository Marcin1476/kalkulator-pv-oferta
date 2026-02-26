import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(page_title="Ekspert PV Pro 2026 - Marcin Szymański", layout="wide")

# --- INICJALIZACJA SESJI ---
if 'lat' not in st.session_state: st.session_state.lat = 52.23
if 'lon' not in st.session_state: st.session_state.lon = 21.01
if 'city' not in st.session_state: st.session_state.city = "Warszawa"

# --- BAZA DANYCH ---
PANELS = {"Longi 450W": 0.450, "Jinko 550W": 0.550, "Trina 400W": 0.400}
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

# --- SIDEBAR: KONFIGURACJA ---
st.sidebar.header("📍 1. Lokalizacja")
city_in = st.sidebar.text_input("Miasto:", value=st.session_state.city)
if st.sidebar.button("Zaktualizuj lokalizację"):
    res_geo = get_coords(city_in)
    if res_geo:
        st.session_state.lat, st.session_state.lon, st.session_state.city = res_geo
        st.rerun()

st.sidebar.header("🏗️ 2. Parametry Dachu")
roof_tilt = st.sidebar.slider("Kąt nachylenia dachu (°)", 0, 90, 35)
roof_dir = st.sidebar.selectbox("Kierunek świata", ["Południe", "Wschód", "Zachód", "Północ"])

st.sidebar.header("🏗️ 3. Kalkulator Mocy i Sprzęt")
sel_p = st.sidebar.selectbox("Model paneli:", list(PANELS.keys()))
num_p = st.sidebar.slider("Liczba paneli:", 1, 60, 14)

panel_power_kwp = PANELS[sel_p]
total_kwp = num_p * panel_power_kwp
st.sidebar.info(f"⚡ Moc projektowana: **{round(total_kwp, 2)} kWp**")

sel_inv = st.sidebar.selectbox("Model inwertera:", list(INVERTERS.keys()))
sel_b = st.sidebar.selectbox("Magazyn energii:", list(BATTERIES.keys()))

st.sidebar.header("💰 4. Koszty i Zużycie")
hp_consumption = st.sidebar.number_input("Roczne zużycie PC (kWh):", 0, 15000, 4000)
price = st.sidebar.number_input("Cena 1 kWh (zł):", 0.5, 3.0, 1.25)
cost_kwp_install = st.sidebar.number_input("Montaż i osprzęt (zł/kWp):", 0, 10000, 4000)

# --- STOPKA SIDEBARU ---
st.sidebar.divider()
st.sidebar.caption("© 2026 Marcin Szymański")
st.sidebar.caption("Wszelkie prawa zastrzeżone")

# --- OBLICZENIA ---
rad_total, sunny_days = get_weather_data(st.session_state.lat, st.session_state.lon)
dir_corr = {"Południe": 1.0, "Wschód": 0.82, "Zachód": 0.82, "Północ": 0.55}
tilt_corr = 1.0 - (abs(roof_tilt - 35) * 0.003) 
final_roof_corr = dir_corr[roof_dir] * tilt_corr
prod_year = total_kwp * rad_total * INVERTERS[sel_inv][0] * final_roof_corr * 0.9
total_investment = (total_kwp * cost_kwp_install) + INVERTERS[sel_inv][1] + (BATTERIES[sel_b] * 2200)
subsidy = (7000 + 16000) if BATTERIES[sel_b] > 0 else 0
net_investment = total_investment - subsidy
base_ac = 0.25 + (BATTERIES[sel_b] / 25) + (0.20 if hp_consumption > 0 else 0)
autocons = min(0.85, base_ac)
savings = (prod_year * autocons * price) + (prod_year * (1 - autocons) * 0.50)
roi = net_investment / savings if savings > 0 else 0

# --- WIDOK GŁÓWNY ---
st.title(f"☀️ Raport Inwestycyjny PV 2026: {st.session_state.city}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Moc Układu", f"{round(total_kwp, 2)} kWp", f"{num_p} szt. x {int(panel_power_kwp*1000)}W")
c2.metric("Dotacja MP 7.0", f"{int(subsidy)} zł")
c3.metric("Koszt NETTO", f"{int(net_investment)} zł")
c4.metric("Czas Zwrotu", f"{round(roi, 1)} lat")

st.divider()

col_map, col_plots = st.columns([1, 1])
with col_map:
    st.subheader("📍 Dane Lokalizacji")
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=12)
    folium.Marker([st.session_state.lat, st.session_state.lon]).add_to(m)
    st_folium(m, height=250, use_container_width=True, key="map_final")
    st.write(f"Dni słoneczne: **{sunny_days}**. Wydajność dachu: **{int(final_roof_corr*100)}%**")

with col_plots:
    st.subheader("📉 Wydajność paneli (25 lat)")
    years_25 = np.arange(1, 26)
    eff = [100 - (y * 0.5) for y in years_25]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(years_25, eff, color='#e67e22', lw=3)
    ax.fill_between(years_25, eff, 80, color='#f39c12', alpha=0.2)
    ax.set_ylim(80, 105)
    ax.set_ylabel("Wydajność (%)")
    st.pyplot(fig)

# --- WIZUALIZACJA PANELI (SYMETRYCZNA) ---
st.subheader("🖼️ Symetryczny Projekt Rozmieszczenia")
cols_n = 8
rows_n = -(-num_p // cols_n)
fig_pv, ax_pv = plt.subplots(figsize=(10, 4))
for i in range(num_p):
    r, c = divmod(i, cols_n)
    is_last_row = (r == rows_n - 1)
    panels_in_last_row = num_p % cols_n
    if is_last_row and panels_in_last_row != 0:
        offset = (cols_n - panels_in_last_row) * 1.3 / 2
        x_pos = (c * 1.3) + offset
    else:
        x_pos = c * 1.3
    y_pos = r * 2.2
    ax_pv.add_patch(patches.Rectangle((x_pos, y_pos), 1.2, 2.0, color='#1a237e', ec='white', lw=0.5))
ax_pv.set_xlim(-0.5, (cols_n * 1.3))
ax_pv.set_ylim(-0.5, (rows_n * 2.2))
ax_pv.set_aspect('equal')
plt.axis('off')
st.pyplot(fig_pv)

# --- STOPKA STRONY GŁÓWNEJ ---
st.markdown("---")
st.markdown("<center><b>© 2026 Marcin Szymański. Wszelkie prawa zastrzeżone.</b></center>", unsafe_allow_html=True)

if st.button("📥 Pobierz Pełną Ofertę PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "RAPORT PV - MOJ PRAD 2026", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Projektant: Marcin Szymanski", ln=True)
    pdf.cell(200, 10, f"Moc instalacji: {round(total_kwp, 2)} kWp", ln=True)
    pdf.cell(200, 10, f"Koszt netto: {int(net_investment)} zl", ln=True)
    pdf.ln(20)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, "Wszelkie prawa zastrzezone (c) Marcin Szymanski", ln=True, align='C')
    res_pdf = pdf.output(dest='S').encode('latin-1')
    st.download_button("Zapisz Raport", res_pdf, "Oferta_Marcin_Szymanski.pdf")
