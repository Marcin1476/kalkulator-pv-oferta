import streamlit as st
import requests
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Ekspert PV - Generator Ofert", layout="wide")

OPERATORS = {"PGE": 1.15, "Tauron": 1.12, "Enea": 1.10, "Energa": 1.18, "Inny": 1.00}
ROOF_TYPES = {"Blachodachówka": 250, "Dachówka": 450, "Dach Płaski": 550, "Grunt": 800}
PANELS_DB = {"Longi 450W": {"power": 0.45, "price": 550}, "Jinko 550W": {"power": 0.55, "price": 700}}
INVERTERS_DB = {"Huawei Sun2000": 4500, "Fronius Symo": 6200, "Growatt MOD": 3800}

st.sidebar.header("📄 Dane Oferty")
client_name = st.sidebar.text_input("Imię i Nazwisko", "Jan Kowalski")
client_addr = st.sidebar.text_input("Adres montażu", "ul. Słoneczna 1, Kraków")

st.sidebar.header("🏗️ Specyfikacja")
selected_panel = st.sidebar.selectbox("Model Panela", list(PANELS_DB.keys()))
num_panels = st.sidebar.slider("Liczba paneli", 1, 60, 12)
selected_roof = st.sidebar.selectbox("Rodzaj dachu", list(ROOF_TYPES.keys()))
selected_inv = st.sidebar.selectbox("Model Inwertera", list(INVERTERS_DB.keys()))
battery_cap = st.sidebar.number_input("Magazyn energii (kWh)", 0, 30, 5)

st.sidebar.header("💰 Finansowanie")
grant = st.sidebar.number_input("Dotacja (zł)", 0, 20000, 6000)
operator = st.sidebar.selectbox("Operator", list(OPERATORS.keys()))

panel_pwr = PANELS_DB[selected_panel]["power"]
total_pwr = num_panels * panel_pwr
area_req = num_panels * 2.0 
hw_cost = (num_panels * PANELS_DB[selected_panel]["price"]) + INVERTERS_DB[selected_inv]
mounting_cost = num_panels * ROOF_TYPES[selected_roof]
net_investment = (hw_cost + mounting_cost + (battery_cap * 2500) - grant) * 0.88

st.title("☀️ System Ofertowy PV")
st.markdown("---")

col_map, col_res = st.columns([2, 1])
with col_map:
    m = folium.Map(location=[52.23, 21.01], zoom_start=6)
    m.add_child(folium.LatLngPopup())
    map_data = st_folium(m, height=400, use_container_width=True)
    lat, lon = (map_data['last_clicked']['lat'], map_data['last_clicked']['lng']) if map_data['last_clicked'] else (52.23, 21.01)

@st.cache_data
def get_solar(lat, lon):
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2023-01-01&end_date=2023-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        return sum(res['daily']['shortwave_radiation_sum']) / 3.6
    except: return 1000.0

rad = get_solar(lat, lon)
yield_kwh = total_pwr * (rad / 1000) * 0.85

with col_res:
    st.metric("Moc", f"{round(total_pwr, 2)} kWp")
    st.metric("Produkcja", f"{int(yield_kwh)} kWh/rok")
    st.metric("Koszt Netto", f"{int(net_investment)} zł")

st.subheader("Wykres i Układ")
c1, c2 = st.columns(2)
with c1:
    fig, ax = plt.subplots()
    ax.plot(range(11), [-net_investment + (i * yield_kwh * 1.1) for i in range(11)])
    ax.axhline(0, color='red')
    st.pyplot(fig)
with c2:
    st.write(f"Układ: {num_panels} paneli na {selected_roof}")
    if st.button("Generuj PDF"):
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, f"OFERTA: {client_name}", ln=True)
        pdf.output("oferta.pdf")
        with open("oferta.pdf", "rb") as f: st.download_button("Pobierz", f, "Oferta.pdf")
