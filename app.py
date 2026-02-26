import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Ekspert PV Pro 2025", layout="wide")

# --- 1. INICJALIZACJA SESJI (MUSI BYĆ NA POCZĄTKU) ---
if 'lat' not in st.session_state:
    st.session_state.lat = 52.23
if 'lon' not in st.session_state:
    st.session_state.lon = 21.01
if 'city' not in st.session_state:
    st.session_state.city = "Warszawa"

# --- FUNKCJE POMOCNICZE ---
def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        res = requests.get(url, headers={'User-Agent': 'PV_App_Final'}).json()
        if res:
            return float(res[0]['lat']), float(res[0]['lon']), res[0]['display_name'].split(',')[0]
    except:
        return None

@st.cache_data
def get_sun_data(lat, lon):
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2025-01-01&end_date=2025-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad = sum([r for r in res['daily']['shortwave_radiation_sum'] if r is not None]) / 3.6
        return rad
    except:
        return 1050.0

# --- 2. PASEK BOCZNY (SIDEBAR) ---
st.sidebar.header("📍 Lokalizacja")
city_in = st.sidebar.text_input("Miasto:", value=st.session_state.city)

if st.sidebar.button("Zastosuj"):
    res = get_coords(city_in)
    if res:
        st.session_state.lat, st.session_state.lon, st.session_state.city = res
        st.rerun()

st.sidebar.header("💰 Finanse i Sprzęt")
bill = st.sidebar.number_input("Rachunek miesięczny (zł):", 50, 2000, 400)
price = st.sidebar.number_input("Cena 1 kWh (zł):", 0.5, 3.0, 1.25)
cost_per_kwp = st.sidebar.number_input("Koszt 1 kWp (zł):", 3000, 7000, 4500)

PANELS = {"Longi 450W": 0.45, "Jinko 550W": 0.55, "Trina 400W": 0.40}
sel_p = st.sidebar.selectbox("Model panela:", list(PANELS.keys()))
num_p = st.sidebar.slider("Liczba paneli:", 1, 60, 14)

BATTERIES = {"Brak": 0, "5 kWh": 5, "10 kWh": 10, "15 kWh": 15}
sel_b = st.sidebar.selectbox("Magazyn energii:", list(BATTERIES.keys()))

# --- 3. OBLICZENIA ---
rad = get_sun_data(st.session_state.lat, st.session_state.lon)
total_kwp = num_p * PANELS[sel_p]
prod_year = total_kwp * (rad * 0.85)
inv_cost = (total_kwp * cost_per_kwp) + (BATTERIES[sel_b] * 2000)
autocons = 0.3 + (BATTERIES[sel_b] / 25) if BATTERIES[sel_b] > 0 else 0.3
autocons = min(0.75, autocons)
savings = (prod_year * autocons * price) + (prod_year * (1 - autocons) * 0.50)
roi = inv_cost / savings if savings > 0 else 0

# --- 4. WIDOK GŁÓWNY ---
st.title(f"☀️ Raport Inwestycyjny: {st.session_state.city}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Moc", f"{round(total_kwp, 2)} kWp")
c2.metric("Inwestycja", f"{int(inv_cost)} zł")
c3.metric("Zysk roczny", f"{int(savings)} zł")
c4.metric("Zwrot", f"{round(roi, 1)} lat")

st.divider()

col_map, col_info = st.columns([2, 1])
with col_map:
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=12)
    folium.Marker([st.session_state.lat, st.session_state.lon]).add_to(m)
    st_folium(m, height=300, use_container_width=True, key="map_final")

with col_info:
    st.subheader("📊 Dane techniczne")
    st.write(f"Produkcja: {int(prod_year)} kWh/rok")
    st.write(f"Autokonsumpcja: {int(autocons*100)}%")
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(['Koszt', 'Zysk 10 lat'], [inv_cost, savings * 10], color=['#34495e', '#27ae60'])
    st.pyplot(fig)

# --- 5. WIZUALIZACJA PANELI ---
st.subheader("🖼️ Projekt rozmieszczenia")
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

# --- 6. PDF ---
if st.button("📥 Generuj PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "OFERTA FOTOWOLTAICZNA 2025", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Miejscowosc: {st.session_state.city}", ln=True)
    pdf.cell(200, 10, f"Moc: {round(total_kwp, 2)} kWp", ln=True)
    pdf.cell(200, 10, f"Zwrot: {round(roi, 1)} lat", ln=True)
    res_pdf = pdf.output(dest='S').encode('latin-1')
    st.download_button("Pobierz Raport PDF", res_pdf, "Oferta_PV.pdf")
