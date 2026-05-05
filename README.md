
# 🚲 JC CitiBike Cycling Tourism Complete Guide

> An interactive data story revealing the spatiotemporal patterns of bike-sharing trips in Jersey City in 2018 through seven visualization chapters.  
> **Live site → [https://gjiawei789-svg.github.io/citibike-story/](https://gjiawei789-svg.github.io/citibike-story/)**

---

## 📂 Repository File List

### 🌐 Front‑end Pages
| File | Description |
|------|-------------|
| `index.html` | Scroll‑driven storytelling main page, integrating all chapters |
| `chapter0_user_type_monthly.html` | Chapter 0: Annual Subscriber vs Customer rides (click‑on‑month interaction) |
| `chapter1_station_heatmap.html` | Chapter 1: August station popularity map (switch between departures/arrivals, bubble size + color) |
| `chapter2_usertype_map.html` | Chapter 2: Tourists vs Locals – side‑by‑side maps of departures and arrivals |
| `chapter3_weather_calendar.html` | Chapter 3: Monthly ridership and weather (temperature, with switchable precipitation/humidity/wind) |
| `chapter4_timeofday_choropleth.html` | Chapter 4: Choropleth by zip code for different time slots + weekly/hourly heatmap |
| `chapter5_daily_average_weekend_ratio.html` | Chapter 5: Weekend daily‑average share, switchable departures/arrivals |
| `chapter6_od_curves.html` | Chapter 6: Top 20 OD curves – total / weekday average / weekend average |

### 🐍 Data Processing & Generation Scripts (Python)
| Script | Purpose |
|--------|---------|
| `html1.py` | Generates `chapter0_user_type_monthly.html` |
| `html2.py` | Generates `chapter1_station_heatmap.html` |
| `html3.py` | Generates `chapter2_usertype_map.html` |
| `html4.py` | Fetches weather data and generates `chapter3_weather_calendar.html` |
| `html5.py` | Generates `chapter4_timeofday_choropleth.html` |
| `html6.py` | Generates `chapter5_daily_average_weekend_ratio.html` |
| `html7.py` | Generates `chapter6_od_curves.html` |

### 📊 Raw Data
- `2018/` folder: contains monthly CitiBike trip records in CSV format.
- Example file name: `JC-201808-citibike-tripdata.csv`

---

## 🚀 How to View the Project

### Option 1: Direct Preview (Recommended)
Click the **Live site** link above, or visit `https://gjiawei789-svg.github.io/citibike-story/`.  
The full scrolling story page will load with all interactive charts embedded – no software installation required.

### Option 2: Local Execution (If you need to regenerate the charts)
1. **Clone the repository**
   ```bash
   git clone https://github.com/gjiawei789-svg/citibike-story.git
   cd citibike-story
   ```

2. **Install Python dependencies**
   Make sure you have Python 3.8+ installed, then run:
   ```bash
   pip install pandas geopandas shapely requests numpy
   ```
   > If you encounter issues installing geopandas, we recommend using [Anaconda](https://www.anaconda.com/) and running: `conda install geopandas shapely`

3. **Prepare the data**
   - Download the raw CitiBike from `https://citibikenyc.com/system-data`
   - Place the raw CitiBike CSV files into the `2018/` folder (file names must contain “2018” and the month, e.g., `201808-citibike-tripdata.csv`).
   - Weather data will be downloaded automatically by `html4.py` from Open‑Meteo (requires internet connection).

4. **Run the generation scripts**
   Execute them one by one:
   ```bash
   python html1.py
   python html2.py
   python html3.py
   python html4.py
   python html5.py
   python html6.py
   python html7.py
   ```
   Each script produces the corresponding HTML file in the current directory.  
   You can also create a batch script to run them all at once.

5. **View the local page**
   - Double‑click `index.html` (some browsers may block iframe loading; in that case start a local server).
   - **Recommended**: from the repository root, run:
     ```bash
     python -m http.server 8000
     ```
     Then open your browser and go to `http://localhost:8000`

---

## 🔧 Tech Stack

- **Data Wrangling**: Python (Pandas, GeoPandas, NumPy)
- **Front‑end Visualisation**:
  - Leaflet (maps)
  - ECharts (bar charts, pie charts, heatmaps)
  - Leaflet.curve (Bézier curves)
- **Storytelling Framework**: Hand‑crafted CSS scroll‑snap + Intersection Observer
- **Deployment**: GitHub Pages

---

**Enjoy the ride! 🚴‍♂️**


