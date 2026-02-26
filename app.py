import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
from datetime import datetime
import folium
from streamlit_folium import st_folium
import io

st.set_page_config(page_title="Ekspert PV Pro", layout="wide")

# --- DANE ---
ROOF_TYPES = {"Blachodachówka": 250, "Dachówka": 450, "Dach Płaski": 550, "Grunt": 800}
PANELS_DB = {"Longi 450W": {"power": 0.45, "w": 1.13, "h": 1.76}, "Jinko 550W": {"power": 0.55, "w": 1.13, "h": 2.27}}

# --- SIDEBAR ---
st.sidebar.header("📄 Dane Klienta")
client_name = st.sidebar.text_input("Imię i Nazwisko", "Jan Kowalski")
client_addr = st.sidebar.text_input("Adres", "ul. Słoneczna 1")

st.sidebar.header("🏗️ Parametry")
sel_panel = st.sidebar.selectbox("Panel", list(PANELS_DB.keys()))
num_panels = st.sidebar.slider("Liczba paneli", 1, 60, 12)
sel_roof = st.sidebar.selectbox("Dach", list(ROOF_TYPES.keys()))
energy_price = st.sidebar.number_input("Twoja cena prądu (zł/kWh)", 0.0, 3.0, 1.15, step=0.01)

# --- OBLICZENIA ---
p_data = PANELS_DB[sel_panel]
total_pwr = num_panels * p_data["power"]
cost_est = (num_panels * 1100) + (num_panels * ROOF_TYPES[sel_roof])

# --- GŁÓWNA SEKCJA ---
st.title("☀️ Generator Oferty Fotowoltaicznej")
col_map, col_info = st.columns([2, 1])

with col_map:
    m = folium.Map(location=[52.23, 21.01], zoom_start=6)
    m.add_child(folium.LatLngPopup())
    map_data = st_folium(m, height=350, use_container_width=True)
    lat, lon = (map_data['last_clicked']['lat'], map_data['last_clicked']['lng']) if map_data['last_clicked'] else (52.23, 21.01)

@st.cache_data
def get_weather_data(lat, lon):
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2024-01-01&end_date=2024-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad_list = res['daily']['shortwave_radiation_sum']
        sunny_days = len([r for r in rad_list if r > 15]) # Próg 15 MJ dla dnia słonecznego
        return sum(rad_list) / 3.6, sunny_days
    except: return 1000.0, 180

rad, sunny_days = get_weather_data(lat, lon)
yield_kwh = total_pwr * (rad / 1000) * 0.85

with col_info:
    st.metric("Liczba dni słonecznych (2024)", f"{sunny_days} dni")
    st.metric("Moc instalacji", f"{round(total_pwr, 2)} kWp")
    st.metric("Szacowany uzysk", f"{int(yield_kwh)} kWh/rok")

# --- WIZUALIZACJA NA DACHU ---
st.subheader("🖼️ Wizualizacja rozmieszczenia paneli")
cols_ui = 6 if num_panels > 6 else num_panels
rows_ui = -(-num_panels // cols_ui)

fig, ax = plt.subplots(figsize=(8, 4))
ax.set_facecolor('#d1d1d1')
for i in range(num_panels):
    r, c = divmod(i, cols_ui)
    rect = patches.Rectangle((c * 1.2, r * 1.9), 1.1, 1.8, linewidth=1, edgecolor='white', facecolor='#1a237e')
    ax.add_patch(rect)

ax.set_xlim(-0.5, cols_ui * 1.3)
ax.set_ylim(-0.5, rows_ui * 2.0)
ax.set_aspect('equal')
plt.axis('off')
st.pyplot(fig)

# --- GENERATOR PDF (NAPRAWIONY) ---
st.divider()
if st.button("📥 Przygotuj Ofertę PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "OFERTA INSTALACJI PV", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Klient: {client_name}", ln=True)
    pdf.cell(200, 10, f"Lokalizacja: {client_addr}", ln=True)
    pdf.cell(200, 10, f"Dni sloneczne w roku ubieglym: {sunny_days}", ln=True)
    pdf.cell(200, 10, f"Moc: {round(total_pwr, 2)} kWp | Cena pradu: {energy_price} zl/kWh", ln=True)
    pdf.cell(200, 10, f"Roczna oszczednosc: {int(yield_kwh * energy_price)} zl", ln=True)
    
    # Przesłanie PDF do Streamlit
    pdf_output = pdf.output(dest='S').encode('latin-1')
    st.download_button(label="Kliknij, aby pobrać plik", data=pdf_output, file_name=f"Oferta_{client_name}.pdf", mime="application/pdf")
