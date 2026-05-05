import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime

try:
    import geopandas as gpd
    from shapely.geometry import Point
except ImportError:
    print("❌ 需要 geopandas 和 shapely，请运行：pip install geopandas shapely")
    raise

# ==================== 配置 ====================
YEAR = 2018
MONTH = 8
DATA_FOLDER = r"E:\data_visual\2018"
OUTPUT_HTML = "chapter4_timeofday_choropleth.html"

NJ_ZIP_GEOJSON_URL = "https://raw.githubusercontent.com/OpenDataDE/State-zip-code-GeoJSON/master/nj_new_jersey_zip_codes_geo.min.json"
# ==============================================

# ---------- 1. 下载并加载 NJ ZIP 边界 ----------
print("正在获取 New Jersey ZIP Code 边界...")
resp = requests.get(NJ_ZIP_GEOJSON_URL, headers={"User-Agent": "Mozilla/5.0"})
resp.raise_for_status()
nj_zips = gpd.read_file(resp.text, driver='GeoJSON')

if 'ZCTA5CE10' in nj_zips.columns:
    nj_zips.rename(columns={'ZCTA5CE10': 'zipcode'}, inplace=True)
elif 'zip_code' in nj_zips.columns:
    nj_zips.rename(columns={'zip_code': 'zipcode'}, inplace=True)
else:
    if 'GEOID10' in nj_zips.columns:
        nj_zips['zipcode'] = nj_zips['GEOID10'].str[-5:]
    else:
        raise KeyError("无法确定邮编列，请检查 GeoJSON 属性：", nj_zips.columns.tolist())

nj_zips = nj_zips[['zipcode', 'geometry']]
nj_zips['zipcode'] = nj_zips['zipcode'].astype(str)
print(f"✅ 已加载 {len(nj_zips)} 个 NJ ZIP 区域")

# ---------- 2. 读取骑行数据 ----------
def load_month_data(folder, year, month):
    frames = []
    target = f"{year}{month:02d}"
    for fname in os.listdir(folder):
        if fname.endswith(".csv") and target in fname:
            path = os.path.join(folder, fname)
            df = pd.read_csv(path, parse_dates=['starttime', 'stoptime'])
            df.rename(columns={
                'start station latitude': 'start_lat',
                'start station longitude': 'start_lng'
            }, inplace=True)
            df['hour'] = df['starttime'].dt.hour
            df['weekday'] = df['starttime'].dt.dayofweek
            frames.append(df)
    if not frames:
        raise FileNotFoundError(f"未找到 {year} 年 {month} 月数据")
    return pd.concat(frames, ignore_index=True)

print(f"读取 {YEAR} 年 {MONTH} 月骑行数据...")
rides = load_month_data(DATA_FOLDER, YEAR, MONTH)

# ---------- 3. 时段定义 ----------
def get_time_slot(hour):
    if 0 <= hour < 4:         return "Early Morning (12AM-4AM)"
    elif 4 <= hour < 8:       return "Morning (5AM-8AM)"
    elif 8 <= hour < 11:      return "Late Morning (9AM-11AM)"
    elif 11 <= hour < 16:     return "Afternoon (12PM-4PM)"
    elif 16 <= hour < 21:     return "Early Evening (5PM-9PM)"
    else:                     return "Late Evening (10PM-11PM)"

rides['time_slot'] = rides['hour'].apply(get_time_slot)

# ---------- 4. 空间连接 ----------
rides['geometry'] = rides.apply(lambda r: Point(r['start_lng'], r['start_lat']), axis=1)
rides_gdf = gpd.GeoDataFrame(rides, geometry='geometry', crs="EPSG:4326")
nj_zips = nj_zips.to_crs("EPSG:4326")

joined = gpd.sjoin(rides_gdf, nj_zips, how='inner', predicate='intersects')
print(f"✅ 空间连接：{len(joined)}/{len(rides)} 条记录匹配到 NJ ZIP 区域")

# ---------- 5. 统计：按时段 + 邮编 ----------
time_slots = [
    "Early Morning (12AM-4AM)",
    "Morning (5AM-8AM)",
    "Late Morning (9AM-11AM)",
    "Afternoon (12PM-4PM)",
    "Early Evening (5PM-9PM)",
    "Late Evening (10PM-11PM)"
]

slot_counts = joined.groupby(['zipcode', 'time_slot']).size().reset_index(name='rides')
zip_rides = {}
for _, row in slot_counts.iterrows():
    zc = str(row['zipcode'])
    if zc not in zip_rides:
        zip_rides[zc] = {slot: 0 for slot in time_slots}
    zip_rides[zc][row['time_slot']] = int(row['rides'])

for zc in nj_zips['zipcode']:
    if zc not in zip_rides:
        zip_rides[zc] = {slot: 0 for slot in time_slots}

# ---------- 6. 热力图数据 ----------
weekday_names = ['周一','周二','周三','周四','周五','周六','周日']
hours = list(range(24))
heatmap_data = np.zeros((7, 24), dtype=int)
weekday_counts = rides.groupby(['weekday', 'hour']).size()
for (wd, hr), val in weekday_counts.items():
    heatmap_data[wd, hr] = int(val)

heatmap_json = {
    "weekdays": weekday_names,
    "hours": [f"{h}:00" for h in hours],
    "data": heatmap_data.tolist()
}

# ---------- 7. 前端数据 ----------
nj_geojson = json.loads(nj_zips.to_json())
data_for_js = {
    "timeSlots": time_slots,
    "zipRides": zip_rides,
    "heatmap": heatmap_json
}

# ---------- 8. 生成HTML（已按要求修改三项） ----------
html_code = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>时段分析与周-小时热力图 | Jersey City</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: -apple-system, sans-serif; }}
        .container {{ display: flex; width: 100%; height: 100vh; }}
        .map-panel {{ flex: 1; position: relative; }}
        .chart-panel {{ flex: 1; background: #f4f6f8; padding: 15px; box-sizing: border-box; }}
        #map {{ width: 100%; height: 100%; }}
        .control-panel {{
            position: absolute;
            top: 15px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
            background: rgba(255,255,255,0.9);
            backdrop-filter: blur(10px);
            padding: 6px 15px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        select {{ padding: 5px 10px; border-radius: 4px; border: 1px solid #ccc; }}
        .current-slot {{
            font-weight: 600;
            color: #2c3e50;
            margin-left: 4px;
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="map-panel">
        <div id="map"></div>
        <div class="control-panel">
            <label for="timeSelect"><strong>⏱️ 时段：</strong></label>
            <select id="timeSelect">
                <option value="Early Morning (12AM-4AM)">🌙 Early Morning (12AM-4AM)</option>
                <option value="Morning (5AM-8AM)">🌅 Morning (5AM-8AM)</option>
                <option value="Late Morning (9AM-11AM)">☀️ Late Morning (9AM-11AM)</option>
                <option value="Afternoon (12PM-4PM)">🌤️ Afternoon (12PM-4PM)</option>
                <option value="Early Evening (5PM-9PM)">🌇 Early Evening (5PM-9PM)</option>
                <option value="Late Evening (10PM-11PM)">🌃 Late Evening (10PM-11PM)</option>
            </select>
            <span class="current-slot" id="slotDisplay"></span>
        </div>
    </div>
    <div class="chart-panel">
        <h4 style="text-align:center; margin:5px 0;">📅 周中每日 · 每小时骑行热力图</h4>
        <div id="heatmapChart" style="width:100%; height:90%;"></div>
    </div>
</div>

<script>
    const GEOJSON_DATA = {json.dumps(nj_geojson, ensure_ascii=False)};
    const RIDES_DATA = {json.dumps(data_for_js, ensure_ascii=False)};

    const map = L.map('map').setView([40.73, -74.06], 12);
    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
        attribution: '&copy; CartoDB',
        maxZoom: 18
    }}).addTo(map);

    function getColor(rides, maxRides) {{
        if (rides === 0) return '#f0f0f0';
        const ratio = Math.min(rides / maxRides, 1);
        const colors = ['#ffffcc','#ffeda0','#fed976','#feb24c','#fd8d3c','#fc4e2a','#e31a1c','#bd0026','#800026'];
        const idx = Math.floor(ratio * (colors.length - 1));
        return colors[idx];
    }}

    function getMaxRides(slot) {{
        const vals = Object.values(RIDES_DATA.zipRides).map(d => d[slot] || 0);
        return Math.max(...vals, 1);
    }}

    function getSlot() {{ return document.getElementById('timeSelect').value; }}

    // 创建 GeoJSON 图层（不添加 ZIP 标签）
    const geoLayer = L.geoJSON(GEOJSON_DATA, {{
        style: function(feature) {{
            const zip = feature.properties.zipcode;
            const slot = getSlot();
            const rides = RIDES_DATA.zipRides[zip] && RIDES_DATA.zipRides[zip][slot] || 0;
            const maxRides = getMaxRides(slot);
            return {{
                fillColor: getColor(rides, maxRides),
                weight: 0.5,
                color: '#666',
                fillOpacity: 0.8
            }};
        }},
        onEachFeature: function(feature, layer) {{
            const zip = feature.properties.zipcode;
            const slot = getSlot();
            const rides = RIDES_DATA.zipRides[zip] && RIDES_DATA.zipRides[zip][slot] || 0;
            layer.bindPopup(`<b>ZIP: ${{zip}}</b><br>骑行次数: ${{rides.toLocaleString()}}`);
            // 移除数字标签，只保留弹窗
        }}
    }}).addTo(map);



    document.getElementById('timeSelect').addEventListener('change', function() {{
        geoLayer.setStyle(function(feature) {{
            const zip = feature.properties.zipcode;
            const slot = getSlot();
            const rides = RIDES_DATA.zipRides[zip] && RIDES_DATA.zipRides[zip][slot] || 0;
            const maxRides = getMaxRides(slot);
            return {{
                fillColor: getColor(rides, maxRides),
                weight: 0.5,
                color: '#666',
                fillOpacity: 0.8
            }};
        }});
        geoLayer.eachLayer(function(layer) {{
            const zip = layer.feature.properties.zipcode;
            const slot = getSlot();
            const rides = RIDES_DATA.zipRides[zip] && RIDES_DATA.zipRides[zip][slot] || 0;
            layer.bindPopup(`<b>ZIP: ${{zip}}</b><br>骑行次数: ${{rides.toLocaleString()}}`);
        }});
        updateSlotDisplay();
    }});

    // ---------- 热力图（标签隐藏，红色渐变，颜色条在上方） ----------
    const heatmapChart = echarts.init(document.getElementById('heatmapChart'));
    const hmData = RIDES_DATA.heatmap.data;
    const seriesData = [];
    for (let wd = 0; wd < 7; wd++) {{
        for (let h = 0; h < 24; h++) {{
            seriesData.push([h, wd, hmData[wd][h]]);
        }}
    }}

    heatmapChart.setOption({{
        tooltip: {{ position: 'top' }},
        grid: {{ left: '12%', right: '8%', top: 50, bottom: 50 }},
        xAxis: {{
            type: 'category',
            data: RIDES_DATA.heatmap.hours,
            splitArea: {{ show: true }}
        }},
        yAxis: {{
            type: 'category',
            data: RIDES_DATA.heatmap.weekdays,
            splitArea: {{ show: true }}
        }},
        visualMap: {{
            min: 0,
            max: Math.max(...seriesData.map(d => d[2]), 1),
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            top: 5,                // 移到上方
            inRange: {{
                color: ['#fff5f0', '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#a50f15', '#67000d']
            }}
        }},
        series: [{{
            type: 'heatmap',
            data: seriesData,
            label: {{ show: false }},      // 不显示数字标签
            emphasis: {{ itemStyle: {{ shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' }} }}
        }}]
    }});

    window.addEventListener('resize', () => {{
        map.invalidateSize();
        heatmapChart.resize();
    }});
</script>
</body>
</html>'''

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html_code)

print(f"✅ Chapter 4 已生成（已去除ZIP标签 / 当前时段文字显示 / 热力图颜色条在上方）：{OUTPUT_HTML}")