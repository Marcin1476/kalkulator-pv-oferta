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
hp_consumption = st.sidebar.number_input("Roczne zużycie Pompy Ciepła (kWh):", 0, 15000, 4000)
price = st.sidebar.number_input("Cena 1 kWh (zł):", 0.5, 3.0, 1.25)
cost_kwp_install = st.sidebar.number_input("Montaż i osprzęt (zł/kWp):", 0, 10000, 4000)

st.sidebar.divider()
st.sidebar.caption("© 2026 Marcin Szymański")

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
st.title(f"☀️ System PV: {st.session_state.city}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Moc Układu", f"{round(total_kwp, 2)} kWp")
c2.metric("Dotacja", f"{int(subsidy)} zł")
c3.metric("Koszt NETTO", f"{int(net_investment)} zł")
c4.metric("Czas Zwrotu", f"{round(roi, 1)} lat")
st.divider()

# --- RAPORT PDF ---
if st.button("📥 GENERUJ PEŁNY RAPORT PDF"):
    pdf = FPDF()
    pdf.add_page()
    
    # Nagłówek
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(200, 10, "KOMPLEKSOWY RAPORT TECHNICZNO-EKONOMICZNY PV", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, f"Projektant: Marcin Szymanski | Data: 2026", ln=True, align='C')
    pdf.ln(10)
    
    # Sekcja 1: Lokalizacja
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "1. LOKALIZACJA I DANE POGODOWE", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(200, 8, f"- Miejscowosc: {st.session_state.city}", ln=True)
    pdf.cell(200, 8, f"- Wspolrzedne: {st.session_state.lat}, {st.session_state.lon}", ln=True)
    pdf.cell(200, 8, f"- Liczba dni slonecznych (2025): {sunny_days}", ln=True)
    pdf.cell(200, 8, f"- Naslonecznienie roczne: {int(rad_total)} kWh/m2", ln=True)
    pdf.ln(5)
    
    # Sekcja 2: Parametry Dachu i Instalacji
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "2. KONFIGURACJA TECHNICZNA", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(200, 8, f"- Kat nachylenia dachu: {roof_tilt} stopni", ln=True)
    pdf.cell(200, 8, f"- Orientacja: {roof_dir}", ln=True)
    pdf.cell(200, 8, f"- Panele: {sel_p} ({num_p} szt.)", ln=True)
    pdf.cell(200, 8, f"- Moc calkowita: {round(total_kwp, 2)} kWp", ln=True)
    pdf.cell(200, 8, f"- Inwerter: {sel_inv}", ln=True)
    pdf.cell(200, 8, f"- Magazyn energii: {sel_b}", ln=True)
    pdf.ln(5)
    
    # Sekcja 3: Bilans Energetyczny
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "3. PROGNOZA PRODUKCJI I ZUZYCIA", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(200, 8, f"- Roczna produkcja energii: {int(prod_year)} kWh", ln=True)
    pdf.cell(200, 8, f"- Uwzglednione zuzycie Pompy Ciepla: {hp_consumption} kWh", ln=True)
    pdf.cell(200, 8, f"- Szacowana autokonsumpcja: {int(autocons*100)}%", ln=True)
    pdf.ln(5)
    
    # Sekcja 4: Analiza Finansowa
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "4. ANALIZA EKONOMICZNA (MOJ PRAD 7.0)", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(200, 8, f"- Koszt inwestycji brutto: {int(total_investment)} zl", ln=True)
    pdf.cell(200, 8, f"- Kwota dotacji: {int(subsidy)} zl", ln=True)
    pdf.cell(200, 8, f"- Koszt inwestycji netto: {int(net_investment)} zl", ln=True)
    pdf.cell(200, 8, f"- Szacowany roczny zysk: {int(savings)} zl", ln=True)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(200, 10, f"- CZAS ZWROTU: {round(roi, 1)} LAT", ln=True)
    
    # Stopka prawna
    pdf.ln(15)
    pdf.set_font("Arial", 'I', 9)
    pdf.multi_cell(0, 5, "Wszelkie prawa autorskie zastrzezone. Dokument wygenerowany przez aplikacje Ekspert PV Pro. Wlasciciel aplikacji: Marcin Szymanski. Kopiowanie i rozpowszechnianie bez zgody autora zabronione.")
    
    res_pdf = pdf.output(dest='S').encode('latin-1')
    st.download_button("KLIKNIJ ABY ZAPISAĆ PDF", res_pdf, f"Raport_PV_{st.session_state.city}_MarcinSzymanski.pdf")

# Reszta wizualizacji (Mapy i Wykresy zostają w aplikacji)
col_map, col_plots = st.columns([1, 1])
with col_map:
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=12)
    folium.Marker([st.session_state.lat, st.session_state.lon]).add_to(m)
    st_folium(m, height=300, use_container_width=True, key="map_final")
with col_plots:
    st.subheader("Symetryczny Układ Paneli")
    # (Tutaj kod wizualizacji symetrycznej z poprzedniego kroku...)
