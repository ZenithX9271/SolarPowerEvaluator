import streamlit as st
import pandas as pd
import numpy as np
import datetime
from geopy.geocoders import Nominatim
import requests
import pvlib
from pvlib.pvsystem import PVSystem
from pvlib.location import Location
from pvlib.modelchain import ModelChain
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Global Solar Power Estimator", layout="wide")
st_autorefresh(interval=300_000, key="autorefresh")

st.title("🌞 Global Solar Energy Estimator")
st.markdown("Estimate solar panel output globally using PVLib, real-time weather & geolocation.")

with st.sidebar:
    st.header("📍 Location & Dates")
    place = st.text_input("Location", "Delhi, India")
    date_main = st.date_input("Primary Date", datetime.date.today())

    st.markdown("---")
    st.header("Panel Specifications")
    panel_type = st.selectbox("Panel Type", ["Monocrystalline", "Polycrystalline", "Perovskite"])
    area = st.number_input("Panel Area (m²)", 0.1, 100.0, 1.6)
    tilt = st.number_input("Tilt Angle (°)", 0.0, 90.0, 28.0)
    azimuth = st.number_input("Azimuth Angle (°)", 0.0, 360.0, 180.0)
    efficiency = st.number_input("Efficiency (%)", 1.0, 30.0, 20.0)

    st.markdown("---")
    st.header("📅 Analysis Range")
    analysis_range = st.selectbox("Select Time Range", ["Single Day", "7 Days", "15 Days", "30 Days", "90 Days", "1 Year", "5 Years"], index=0)

@st.cache_data(show_spinner=False)
def geocode(place_name):
    geo = Nominatim(user_agent="solar_estimator")
    loc = geo.geocode(place_name)
    return (loc.latitude, loc.longitude) if loc else (None, None)

@st.cache_data(show_spinner=False)
def fetch_weather(lat, lon, date):
    start = date.strftime("%Y-%m-%dT00:00")
    end = date.strftime("%Y-%m-%dT23:00")
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&hourly=temperature_2m,wind_speed_10m,cloud_cover"
        f"&start={start}&end={end}&timezone=auto"
    )
    r = requests.get(url, timeout=10)
    df = pd.DataFrame(r.json()["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    df.set_index("time", inplace=True)
    return df

def compute_irradiance(df_weather, location):
    times = df_weather.index
    clearsky = location.get_clearsky(times)
    solar_pos = location.get_solarposition(times)
    zenith = solar_pos["zenith"]

    ghi = clearsky["ghi"] * (1 - df_weather["cloud_cover"] / 100)
    dni = pvlib.irradiance.disc(ghi, zenith, times)["dni"]
    dhi = ghi - dni * np.cos(np.radians(zenith))

    return ghi, dni, dhi, solar_pos

def simulate_power(df_weather, ghi, dni, dhi, solar_pos, location):
    times = df_weather.index
    temp_air = df_weather["temperature_2m"]
    wind = df_weather["wind_speed_10m"]

    pdc0 = area * (efficiency / 100.0) * 1000.0
    system = PVSystem(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        module_parameters={"pdc0": pdc0, "gamma_pdc": -0.004},
        inverter_parameters={"pdc0": pdc0},
        temperature_model_parameters=pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_glass"],
    )

    mc = ModelChain(system, location, ac_model="pvwatts", aoi_model="no_loss")

    df_input = pd.DataFrame({
        "ghi": ghi,
        "dni": dni,
        "dhi": dhi,
        "temp_air": temp_air,
        "wind_speed": wind
    }, index=times)

    mc.run_model(df_input)
    ac = mc.results.ac.fillna(0)
    energy_kwh = ac.resample("H").sum().sum() / 1000.0
    return ac, energy_kwh, ghi, temp_air, wind

lat, lon = geocode(place)
if lat is None:
    st.error("Could not locate place.")
    st.stop()

location = Location(lat, lon)
range_days = {"Single Day": 1, "7 Days": 7, "15 Days": 15, "30 Days": 30, "90 Days": 90, "1 Year": 365, "5 Years": 1825}

results_energy = []
full_power_series = []
full_irradiance = []
full_temperature = []
full_wind = []

date_list = [date_main + datetime.timedelta(days=i) for i in range(range_days[analysis_range])]

for dt in date_list:
    df_weather = fetch_weather(lat, lon, dt)
    ghi, dni, dhi, solarpos = compute_irradiance(df_weather, location)
    ac, energy, g, t, w = simulate_power(df_weather, ghi, dni, dhi, solarpos, location)

    results_energy.append({"date": dt, "energy": energy})
    full_power_series.append(ac)
    full_irradiance.append(g)
    full_temperature.append(t)
    full_wind.append(w)

df_power = pd.concat(full_power_series)
df_irr = pd.concat(full_irradiance)
df_temp = pd.concat(full_temperature)
df_wind = pd.concat(full_wind)

st.subheader("📊 Trends over Selected Time Range")
col3, col4 = st.columns(2)
with col3:
    st.markdown("<div style='text-align: center; font-weight: bold;'>AC Power (W)</div>", unsafe_allow_html=True)
    st.line_chart(df_power.rename("AC Power (W)"), height=300)
with col4:
    st.markdown("<div style='text-align: center; font-weight: bold;'>Irradiance (W/m²)</div>", unsafe_allow_html=True)
    st.line_chart(df_irr.rename("Irradiance (W/m²)"), height=300)
col5, col6 = st.columns(2)
with col5:
    st.markdown("<div style='text-align: center; font-weight: bold;'>Temperature (°C)</div>", unsafe_allow_html=True)
    st.line_chart(df_temp.rename("Temperature (°C)"), height=300)
with col6:
    st.markdown("<div style='text-align: center; font-weight: bold;'>Wind Speed (m/s)</div>", unsafe_allow_html=True)
    st.line_chart(df_wind.rename("Wind Speed (m/s)"), height=300)

total_df = pd.DataFrame(results_energy)
st.subheader(f"📈 Energy Profile — {place} from {date_list[0]} to {date_list[-1]}")
st.line_chart(total_df.set_index("date"))
st.success(f"🔋 Total Estimated Energy over Period: `{total_df['energy'].sum():.2f} kWh`")
