import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Ekspert PV Pro 2025", layout="wide")

# --- BAZA PANELI ---
PANELS_DB = {
    "Longi 450W": 0.45,
    "Jinko 550W": 0.55,
    "Trina 400W": 0.40,
    "Canadian Solar 600W": 0.60
}

def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'Kalkulator_PV_2025_Final'}
        response = requests.get(url, headers=headers).json()
        if response:
            return float(response[0]['lat']), float(response[0]['lon']), response[0]['display_name'].split(',')[0]
    except:
        return None
    return None

@st.cache_data
def get_weather_2025(lat, lon):
    try:
        # Dane za cały rok 2025
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2025-01-01&end_date=2025-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad_list = res['daily']['shortwave_radiation_sum']
        
        # Liczymy dni słoneczne (> 18 MJ/m2)
        sunny_days = len([r for r in rad_list if r is not None and r > 18])
        # Średnie nasłonecznienie na m2 w kWh
        total_rad_kwh_per_m2 = sum([r for r in rad_list if r is not None]) / 3.6
        return total_rad_kwh_per_m2, sunny_days
    except:
        return 1050.0, 190

# --- SESJA I LOKALIZACJA ---
if 'lat' not in st.session_state:
    st.session_state.lat, st.session_state.lon = 52.2297, 21.0122
    st.session_state.city_name = "Warszawa"

# --- SIDEBAR ---
st.sidebar.header("📍 1. Lokalizacja (Dane 2025)")
city_query = st.sidebar.text_input("Wpisz miasto:", st.session_state.city_name)

if st.sidebar.button("Zastosuj lokalizację"):
    res = get_coords(city_query)
    if res:
        st.session_state.lat, st.session_state.lon, st.session_state.city_name = res
        st.rerun()
    else:
        st.sidebar.error("Nie znaleziono miejscowości.")

st.sidebar.header("🏗️ 2. Konfiguracja Sprzętu")
# WYBÓR PANELI (Przywrócony)
selected_panel_name = st.sidebar.selectbox("Wybierz model panela:", list(PANELS_DB.keys()))
panel_power = PANELS_DB[selected_panel_name]

num_panels = st.sidebar.slider("Liczba paneli (szt.):", 1, 100, 14)
energy_price = st.sidebar.number_input("Twoja cena prądu (zł/kWh):", 0.0, 4.0, 1.25)

# --- OBLICZENIA ---
rad_per_m2, sunny_days_2025 = get_weather_2025(st.session_state.lat, st.session_state.lon)

# Łączna moc instalacji (kWp)
total_kwp = num_panels * panel_power

# Obliczenie całkowitej produkcji (mnożymy nasłonecznienie przez moc instalacji i sprawność układu ok. 85%)
total_production_kwh = total_kwp * (rad_per_m2 / 1000) * 1000 * 0.85 
# Prostszy wzór: Produkcja = moc instalacji * współczynnik nasłonecznienia (kWh/kWp)
actual_yield = total_kwp * (rad_per_m2 * 0.85)

annual_profit = actual_yield * energy_price

# --- INTERFEJS ---
st.title(f"☀️ Raport Energii 2025: {st.session_state.city_name}")
st.info(f"Wybrany sprzęt: {selected_panel_name} ({panel_power} kWp/szt.) | Łączna moc: {round(total_kwp, 2)} kWp")

c1, c2 = st.columns([2, 1])

with c1:
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=11)
    folium.Marker([st.session_state.lat, st.session_state.lon], popup=st.session_state.city_name).add_to(m)
    st_folium(m, height=400, use_container_width=True, key="map_final_2025")

with c2:
    st.subheader("Wyniki dla całego systemu")
    st.metric("Dni słoneczne (2025)", f"{sunny_days_2025} dni")
    st.metric("Łączna produkcja", f"{int(actual_yield)} kWh / rok")
    st.success(f"Oszczędność: {int(annual_profit)} zł / rok")
    st.write(f"Nasłonecznienie lokalne: {int(rad_per_m2)} kWh/m²")

st.divider()

# --- WIZUALIZACJA ---
st.subheader("🖼️ Rozmieszczenie wybranych paneli")
cols = 8 if num_panels > 8 else num_panels
rows = -(-num_panels // cols)
fig, ax = plt.subplots(figsize=(10, 4))
ax.set_facecolor('#eceff1')

for i in range(num_panels):
    r, c = divmod(i, cols)
    ax.add_patch(patches.Rectangle((c * 1.3, r * 2.2), 1.2, 2.0, color='#1a237e', ec='white', lw=1))

plt.axis('off')
ax.set_xlim(-1, cols * 1.5)
ax.set_ylim(-1, rows * 2.5)
st.pyplot(fig)

# --- PDF ---
if st.button("📥 Generuj Ofertę PDF"):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, f"OFERTA ENERGII 2025 - {st.session_state.city_name.upper()}", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", '', 12)
        pdf.cell(200, 10, f"Miejscowosc: {st.session_state.city_name}", ln=True)
        pdf.cell(200, 10, f"Wybrane panele: {num_panels}x {selected_panel_name}", ln=True)
        pdf.cell(200, 10, f"Laczna moc instalacji: {round(total_kwp, 2)} kWp", ln=True)
        pdf.cell(200, 10, f"Dni sloneczne w 2025: {sunny_days_2025}", ln=True)
        pdf.cell(200, 10, f"Roczna produkcja energii: {int(actual_yield)} kWh", ln=True)
        pdf.cell(200, 10, f"Roczny zysk finansowy: {int(annual_profit)} zl", ln=True)
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        st.download_button(label="Pobierz PDF", data=pdf_bytes, file_name=f"Oferta_{st.session_state.city_name}.pdf", mime="application/pdf")
    except Exception as e:
        st.error(f"Błąd PDF: {e}")
