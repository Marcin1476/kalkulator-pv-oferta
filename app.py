import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(page_title="Ekspert PV & PC Pro 2025", layout="wide")

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
# Pompy ciepła: [Cena bazowa z montażem zł, Średni SCOP]
HEAT_PUMPS = {
    "Brak": [0, 0],
    "Pompa 5 kW (Mały dom)": [32000, 4.0],
    "Pompa 7 kW (Średni dom)": [38000, 3.9],
    "Pompa 9 kW (Duży dom)": [45000, 3.8],
    "Pompa 12 kW (Dom 200m2+)": [52000, 3.7]
}

# --- FUNKCJE ---
def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        res = requests.get(url, headers={'User-Agent': 'PV_PC_Pro_V9'}).json()
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
if st.sidebar.button("Zaktualizuj dane"):
    res = get_coords(city_in)
    if res:
        st.session_state.lat, st.session_state.lon, st.session_state.city = res
        st.rerun()

st.sidebar.header("🏗️ 2. Sprzęt PV")
sel_p = st.sidebar.selectbox("Model paneli:", list(PANELS.keys()))
num_p = st.sidebar.slider("Liczba paneli:", 1, 60, 14)
sel_inv = st.sidebar.selectbox("Model inwertera:", list(INVERTERS.keys()))
sel_b = st.sidebar.selectbox("Magazyn energii:", list(BATTERIES.keys()))

st.sidebar.header("🔥 3. Pompa Ciepła")
sel_hp = st.sidebar.selectbox("Dobór pompy ciepła:", list(HEAT_PUMPS.keys()))
hp_thermal_need = st.sidebar.number_input("Zapotrzebowanie na ciepło (kWh/rok):", 5000, 30000, 12000, step=1000)

st.sidebar.header("💰 4. Finanse")
bill = st.sidebar.number_input("Rachunek za prąd (miesięczny):", 50, 2000, 400)
price = st.sidebar.number_input("Cena 1 kWh (zł):", 0.5, 3.0, 1.25)
cost_kwp = st.sidebar.number_input("Montaż i osprzęt PV (zł/kWp):", 0, 10000, 4000)

# --- OBLICZENIA ---
rad_total, sunny_days = get_weather_data(st.session_state.lat, st.session_state.lon)
total_kwp = num_p * PANELS[sel_p]
inv_eff = INVERTERS[sel_inv][0]
inv_price = INVERTERS[sel_inv][1]

# Produkcja PV
prod_year = total_kwp * rad_total * inv_eff * 0.9

# Zużycie Pompy Ciepła
hp_cost, hp_scop = HEAT_PUMPS[sel_hp]
hp_consumption = (hp_thermal_need / hp_scop) if hp_scop > 0 else 0
base_consumption = (bill / price) * 12
total_yearly_need = base_consumption + hp_consumption

# Finanse
total_investment = (total_kwp * cost_kwp) + inv_price + (BATTERIES[sel_b] * 2000) + hp_cost

# Zwiększona autokonsumpcja przy pompie ciepła
ac_bonus = 0.15 if hp_consumption > 0 else 0
autocons_val = 0.3 + (BATTERIES[sel_b] / 25) + ac_bonus
autocons = min(0.85, autocons_val)

yearly_savings = (prod_year * autocons * price) + (prod_year * (1 - autocons) * 0.50)
# Uniknięty koszt zakupu prądu dla pompy ciepła
if hp_consumption > 0:
    yearly_savings += (hp_consumption * 0.4 * price) # szacunkowy zysk z PV dla PC

roi = total_investment / yearly_savings if yearly_savings > 0 else 0

# --- WIDOK GŁÓWNY ---
st.title(f"☀️ Raport Techniczny PV + PC 2025: {st.session_state.city}")

col_top1, col_top2, col_top3, col_top4 = st.columns(4)
col_top1.metric("Moc Instalacji", f"{round(total_kwp, 2)} kWp")
col_top2.metric("Zużycie Pompy", f"{int(hp_consumption)} kWh/rok")
col_top3.metric("Inwestycja Total", f"{int(total_investment)} zł")
col_top4.metric("Zwrot (ROI)", f"{round(roi, 1)} lat")

st.divider()

col_map, col_plots = st.columns([1, 1])

with col_map:
    st.subheader("📍 Analiza i Dobór")
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=12)
    folium.Marker([st.session_state.lat, st.session_state.lon]).add_to(m)
    st_folium(m, height=250, use_container_width=True, key="map_v10")
    
    st.write(f"🏠 **Zapotrzebowanie domu:** {int(total_yearly_need)} kWh/rok")
    st.write(f"📉 **Stopień autokonsumpcji:** {int(autocons*100)}%")
    if sel_hp != "Brak":
        st.success(f"Wybrano pompę o mocy: **{sel_hp}**. Szacowany współczynnik SCOP: **{hp_scop}**")

with col_plots:
    st.subheader("📈 Wykres Cash Flow (PV + PC)")
    years = np.arange(0, 16)
    cash_flow = [-total_investment + (y * yearly_savings) for y in years]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(years, cash_flow, marker='o', color='#2c3e50', lw=2)
    ax.fill_between(years, cash_flow, 0, where=(np.array(cash_flow) < 0), color='#e74c3c', alpha=0.3)
    ax.fill_between(years, cash_flow, 0, where=(np.array(cash_flow) >= 0), color='#2ecc71', alpha=0.3)
    ax.axhline(0, color='black', ls='-', lw=1)
    ax.set_xlabel("Lata")
    ax.set_ylabel("Bilans (zł)")
    st.pyplot(fig)



# --- WIZUALIZACJA PROJEKTU ---
st.subheader("🖼️ Projekt Rozmieszczenia Paneli")
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

if st.button("📥 Generuj Pełną Ofertę PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "RAPORT HYBRYDOWY: FOTOWOLTAIKA + POMPA CIEPLA", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Lokalizacja: {st.session_state.city}", ln=True)
    pdf.cell(200, 10, f"System PV: {num_p}x {sel_p} ({round(total_kwp, 2)} kWp)", ln=True)
    pdf.cell(200, 10, f"Pompa ciepla: {sel_hp} (SCOP: {hp_scop})", ln=True)
    pdf.cell(200, 10, f"Inwestycja laczna: {int(total_investment)} zl", ln=True)
    pdf.cell(200, 10, f"Szacowany okres zwrotu: {round(roi, 1)} lat", ln=True)
    res_pdf = pdf.output(dest='S').encode('latin-1')
    st.download_button("Pobierz Plik PDF", res_pdf, "Oferta_Hybrydowa_2025.pdf")
