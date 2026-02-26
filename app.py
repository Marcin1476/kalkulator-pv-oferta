import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Ekspert PV Pro 2025", layout="wide")

def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'Kalkulator_PV_2025_App'}
        response = requests.get(url, headers=headers).json()
        if response:
            return float(response[0]['lat']), float(response[0]['lon']), response[0]['display_name'].split(',')[0]
    except:
        return None
    return None

@st.cache_data
def get_weather_2025(lat, lon):
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2025-01-01&end_date=2025-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad_list = res['daily']['shortwave_radiation_sum']
        sunny_days = len([r for r in rad_list if r is not None and r > 18])
        total_rad_kwh = sum([r for r in rad_list if r is not None]) / 3.6
        return total_rad_kwh, sunny_days
    except:
        return 1050.0, 190

if 'lat' not in st.session_state:
    st.session_state.lat, st.session_state.lon = 52.2297, 21.0122
    st.session_state.city_name = "Warszawa"

st.sidebar.header("📍 Lokalizacja (Dane 2025)")
city_query = st.sidebar.text_input("Wpisz miasto:", st.session_state.city_name)

if st.sidebar.button("Zastosuj i przelicz dla 2025"):
    res = get_coords(city_query)
    if res:
        st.session_state.lat, st.session_state.lon, st.session_state.city_name = res
        st.rerun()
    else:
        st.sidebar.error("Nie znaleziono miejscowości.")

st.sidebar.header("🏗️ Parametry")
num_panels = st.sidebar.slider("Liczba paneli:", 1, 80, 14)
energy_price = st.sidebar.number_input("Cena energii (zł/kWh):", 0.0, 3.5, 1.25)

rad_2025, sunny_days_2025 = get_weather_2025(st.session_state.lat, st.session_state.lon)
total_kwp = num_panels * 0.45
production = total_kwp * (rad_2025 / 1000) * 0.85
annual_profit = production * energy_price

st.title(f"☀️ Raport Nasłonecznienia 2025: {st.session_state.city_name}")

c1, c2 = st.columns([2, 1])

with c1:
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=11)
    folium.Marker([st.session_state.lat, st.session_state.lon], popup=st.session_state.city_name).add_to(m)
    st_folium(m, height=400, use_container_width=True, key="map_unique_2025")

with c2:
    st.subheader("Statystyki za rok 2025")
    st.metric("Dni słoneczne", f"{sunny_days_2025} dni")
    st.metric("Suma energii", f"{int(rad_2025)} kWh/m²")
    st.success(f"Zysk: {int(annual_profit)} zł/rok")

st.divider()

st.subheader("🖼️ Rozmieszczenie paneli na dachu")
cols = 7 if num_panels > 7 else num_panels
rows = -(-num_panels // cols)
fig, ax = plt.subplots(figsize=(10, 4))
ax.set_facecolor('#cfd8dc')

for i in range(num_panels):
    r, c = divmod(i, cols)
    ax.add_patch(patches.Rectangle((c * 1.3, r * 2.1), 1.2, 2.0, color='#0d47a1', ec='white', lw=1.5))

plt.axis('off')
ax.set_xlim(-1, cols * 1.5)
ax.set_ylim(-1, rows * 2.5)
st.pyplot(fig)

if st.button("📥 Generuj Ofertę PDF"):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "OFERTA PV 2025", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", '', 12)
        pdf.cell(200, 10, f"Lokalizacja: {st.session_state.city_name}", ln=True)
        pdf.cell(200, 10, f"Dni sloneczne (2025): {sunny_days_2025}", ln=True)
        pdf.cell(200, 10, f"Moc: {round(total_kwp, 2)} kWp", ln=True)
        
        pdf_out = pdf.output(dest='S').encode('latin-1')
        st.download_button(label="Pobierz PDF", data=pdf_out, file_name="oferta.pdf", mime="application/pdf")
    except Exception as e:
        st.error(f"Błąd generowania PDF: {e}")
