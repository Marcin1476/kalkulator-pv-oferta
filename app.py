import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Ekspert PV Pro 2025", layout="wide")

# --- KONFIGURACJA DANYCH ---
PANELS_DB = {"Longi 450W": 0.45, "Jinko 550W": 0.55, "Trina 400W": 0.40}
BATTERY_DB = {"Brak": 0, "5 kWh": 5, "10 kWh": 10, "15 kWh": 15}

def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'Kalkulator_PV_Final'}
        res = requests.get(url, headers=headers).json()
        if res: return float(res[0]['lat']), float(res[0]['lon']), res[0]['display_name'].split(',')[0]
    except: return None

@st.cache_data
def get_weather_2025(lat, lon):
    try:
        # Pobieranie danych nasłonecznienia za rok 2025
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2025-01-01&end_date=2025-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad_list = res['daily']['shortwave_radiation_sum']
        sunny_days = len([r for r in rad_list if r is not None and r > 18])
        total_rad_kwh = sum([r for r in rad_list if r is not None]) / 3.6
        return total_rad_kwh, sunny_days
    except: return 1050.0, 190

# Inicjalizacja sesji
if 'lat' not in st.session_state:
    st.session_state.lat, st.session_state.lon, st.session_state.city_name = 52.23, 21.01, "Warszawa"

# --- SIDEBAR: KONFIGURACJA ---
st.sidebar.header("📍 1. Lokalizacja (Dane 2025)")
city_input = st.sidebar.text_input("Wpisz miasto:", st.session_state.city_name)
if st.sidebar.button("Zastosuj i przelicz"):
    res = get_coords(city_input)
    if res:
        st.session_state.lat, st.session_state.lon, st.session_state.city_name = res
        st.rerun()

st.sidebar.header("💰 2. Bilans Energii")
monthly_bill = st.sidebar.number_input("Rachunek miesięczny (zł):", 50, 2000, 350)
energy_price = st.sidebar.number_input("Cena za 1 kWh (zł):", 0.5, 3.0, 1.25)

st.sidebar.header("🏗️ 3. Sprzęt")
sel_panel = st.sidebar.selectbox("Model panela:", list(PANELS_DB.keys()))
num_panels = st.sidebar.slider("Liczba paneli:", 1, 60, 14)
sel_battery = st.sidebar.selectbox("Magazyn energii:", list(BATTERY_DB.keys()))

# --- OBLICZENIA LOGICZNE ---
rad_m2, sunny_days = get_weather_2025(st.session_state.lat, st.session_state.lon)
total_kwp = num_panels * PANELS_DB[sel_panel]
production_kwh = total_kwp * (rad_m2 * 0.85)
annual_usage_kwh = (monthly_bill / energy_price) * 12

# Szacowanie oszczędności (autokonsumpcja)
autocons = 0.3 + (BATTERY_DB[sel_battery] / 25) if BATTERY_DB[sel_battery] > 0 else 0.3
autocons = min(0.75, autocons)
annual_savings = (production_kwh * autocons * energy_price) + (production_kwh * (1 - autocons) * 0.50)
new_annual_bill = max(300, (annual_usage_kwh * energy_price) - annual_savings)
total_profit = (annual_usage_kwh * energy_price) - new_annual_bill

# --- INTERFEJS GŁÓWNY ---
st.title(f"☀️ Raport Energetyczny 2025: {st.session_state.city_name}")

c1, c2, c3 = st.columns(3)
c1.metric("Zużycie domu", f"{int(annual_usage_kwh)} kWh/rok")
c2.metric("Produkcja PV", f"{int(production_kwh)} kWh/rok")
c3.metric("Roczny zysk", f"{int(total_profit)} zł")

st.divider()

col_m, col_b = st.columns([2, 1])
with col_m:
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=12)
    folium.Marker([st.session_state.lat, st.session_state.lon]).add_to(m)
    st_folium(m, height=300, use_container_width=True, key="stable_map")

with col_b:
    st.subheader("📊 Bilans kosztów")
    fig, ax = plt.subplots()
    ax.bar(['Przed PV', 'Po montażu'], [annual_usage_kwh * energy_price, new_annual_bill], color=['#e74c3c', '#2ecc71'])
    ax.set_ylabel("Roczny koszt (zł)")
    st.pyplot(fig)

# --- WIZUALIZACJA PROJEKTU ---
st.subheader("🖼️ Rozmieszczenie paneli (Widok projektowy)")
cols = 8
rows = -(-num_panels // cols)
fig_pv, ax_pv = plt.subplots(figsize=(10, 3))
ax_pv.set_facecolor('#fdfdfd')
for i in range(num_panels):
    r, c = divmod(i, cols)
    ax_pv.add_patch(patches.Rectangle((c*1.3, r*2.2), 1.2, 2.0, color='#1a237e', ec='white', lw=1))
plt.axis('off')
st.pyplot(fig_pv)

# --- PDF ---
if st.button("📥 Pobierz Ofertę PDF"):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, f"OFERTA PV 2025 - {st.session_state.city_name.upper()}", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", '', 12)
        pdf.cell(200, 10, f"Lokalizacja: {st.session_state.city_name}", ln=True)
        pdf.cell(200, 10, f"Moc: {round(total_kwp, 2)} kWp | Magazyn: {sel_battery}", ln=True)
        pdf.cell(200, 10, f"Dni sloneczne: {sunny_days}", ln=True)
        pdf.cell(200, 10, f"Oszczednosc roczna: {int(total_profit)} PLN", ln=True)
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        st.download_button("Zapisz PDF", pdf_bytes, "Oferta_PV.pdf", "application/pdf")
    except Exception as e:
        st.error(f"Błąd PDF: {e}")
