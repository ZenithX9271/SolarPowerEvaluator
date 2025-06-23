# 🌞 Global Solar Energy Estimator

**A Streamlit web application for real-time and historical solar energy analysis using PVLib and geospatial/weather APIs.**

---

## Project Overview

This tool enables users to estimate and visualize solar panel performance across any global location. It combines:

* **Geocoding**: Convert place names to latitude/longitude via GeoPy.
* **Weather Integration**: Fetch real-time and forecast data (temperature, wind speed, cloud cover) from Open-Meteo.
* **Solar Geometry & Irradiance**: Compute solar position, clearsky GHI, DNI, DHI using PVLib models (ineichen, DISC).
* **PV System Modeling**: Simulate DC and AC power output using PVWatts, SAPM, and inverter models.
* **Interactive Visualizations**: Dynamic charts for power, irradiance, temperature, wind over selectable time ranges.
* **Flexible Analysis Ranges**: Single day up to 5-year trends.

This README documents every feature, implementation detail, and underlying theory.

---

## Table of Contents

1. [Features](#features)
2. [Installation](#installation)
3. [Usage](#usage)
4. [Architecture & Code Structure](#architecture--code-structure)
5. [Feature Deep Dive](#feature-deep-dive)

   * Geocoding
   * Weather Data Integration
   * Solar Geometry & Irradiance Models
   * PV System Modeling (PVLib)
   * Time Range Analysis
   * Visualizations
6. [Theory & References](#theory--references)
7. [Contributing](#contributing)
8. [License](#license)

---

## Features

* **Global Geocoding**: Enter any location name; the app auto-fetches coordinates.
* **Real-Time & Historical Weather**: Uses Open-Meteo API to retrieve hourly temperature, wind speed, cloud cover.
* **PVLib Integration**:

  * **Solar Position**: Calculate solar zenith, azimuth for each timestamp.
  * **Clearsky Models**: Ineichen–Perez model for clear-sky GHI.
  * **Irradiance Decomposition**: DISC model for DNI, derived DHI.
* **PV System Simulation**:

  * **Module Parameters**: Configurable area, tilt, azimuth, efficiency.
  * **Temperature Effects**: SAPM cell temperature model.
  * **DC Performance**: Sandia Array Performance Model (SAPM).
  * **AC Inverter**: PVWatts model for AC power.
* **Dynamic Analysis Ranges**: From single day to 5-year aggregated trends.
* **Interactive Charts**: Top-of-page charts update immediately when range changes.
* **Daily Energy Trends**: Aggregated kWh per day over selected period.

---


## Usage

1. **Enter a location** (city, region, or address) in the sidebar.
2. **Choose the primary date** and **analysis range** (Single Day, 7 Days, …, 5 Years).
3. **Configure panel specs**: type, area (m²), tilt (°), azimuth (°), efficiency (%).
4. View **four key charts** at the top for power, irradiance, temperature, wind.
5. Scroll to see the **daily energy trend** and total kWh generated.
6. Modify inputs and watch charts update in real time.

---

## Architecture & Code Structure

```
├── app.py            # Main Streamlit application
├── requirements.txt  # Python dependencies
├── README.md         # This documentation
└── .streamlit/       # Streamlit config (optional)
```

**Key Modules**:

* `geocode()`: GeoPy to convert location names.
* `fetch_weather()`: Requests to Open-Meteo, parsing JSON to pandas.
* `compute_irradiance()`: PVLib clearsky + DISC decomposition.
* `simulate_power()`: PVSystem & ModelChain for DC/AC simulation.
* **Main Loop**: Iterates over each day in selected range, aggregates series.
* **Visuals**: Streamlit `st.line_chart`, `st.columns`, center-aligned HTML captions.

---

##  Feature Deep Dive

### 1. Geocoding

* Uses **Nominatim** (OpenStreetMap) via GeoPy.
* Returns `(latitude, longitude)` for any text input.
* Cached to avoid repeated API calls (`@st.cache_data`).

### 2. Weather Data Integration

* Fetches hourly **temperature**, **wind speed**, and **cloud cover**.
* **Open-Meteo API** endpoint:

  ```
  https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,wind_speed_10m,cloud_cover&start={date}T00:00&end={date}T23:00&timezone=auto
  ```
* Data parsed into a **pandas.DataFrame** indexed by timestamp.

### 3. Solar Geometry & Irradiance Models

* **Solar Position**: `Location.get_solarposition()` computes zenith & azimuth.
* **Clearsky (Ineichen)**: `Location.get_clearsky()` for clear-sky GHI.
* **Irradiance Decomposition**:

  * **DISC model** (`pvlib.irradiance.disc`) yields DNI.
  * **DHI** computed as: $DHI = GHI - DNI \times \cos(zenith)$.

### 4. PV System Modeling (PVLib)

* **PVSystem** parameters:

  * `surface_tilt`, `surface_azimuth`.
  * `module_parameters`: `pdc0` (area×eff), `gamma_pdc`.
  * `inverter_parameters`: `pdc0` for PVWatts.
  * `temperature_model_parameters`: SAPM open-rack glass–glass.
* **ModelChain**:

  * `ac_model="pvwatts"` for AC conversion.
  * `aoi_model="no_loss"` to skip angle-of-incidence losses.
* **Outputs**:

  * `mc.results.ac`: AC power (W) time series.
  * Aggregate to hourly energy: $\text{kWh} = \sum(ac)/1000$.

### 5. Time Range Analysis

* **`analysis_range`** mapping to days: Single Day → 1, 7 Days → 7, …, 5 Years → 1825.
* Loop over each date: fetch weather, compute irradiance & power, store series.
* **Concatenate** full time series for power, irradiance, temperature, wind.

### 6. Visualizations

* **Top Charts** (in page header area): Four charts in a 2×2 grid:

  1. AC Power (W)
  2. Irradiance (W/m²)
  3. Temperature (°C)
  4. Wind Speed (m/s)
* **Captions**: Centered bold labels below each chart with HTML via `st.markdown(..., unsafe_allow_html=True)`.
* **Daily Energy Trend**: Line chart of kWh per day.
* **Metrics**: `st.success()` showing total kWh over selected range.

---

## Theory & References

* **Solar Geometry**: Declination, Hour angle, Zenith angle formulas (Tiwari & Dubey, ESL100 lecture).
* **Air Mass & Irradiance**: Beer–Lambert law, AM1.5 standard spectrum.
* **PVLib Docs**: [https://pvlib-python.readthedocs.io/](https://pvlib-python.readthedocs.io/)
* **Open-Meteo API**: [https://open-meteo.com/](https://open-meteo.com/)
* **GeoPy (Nominatim)**: [https://geopy.readthedocs.io/](https://geopy.readthedocs.io/)

---

## Contributing

Contributions, issues, and feature requests are welcome! Please fork the repo and submit a pull request.

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.
