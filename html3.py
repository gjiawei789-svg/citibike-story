import pandas as pd
import os
import json

# ==================== 配置 ====================
DATA_FOLDER = r"E:\data_visual\2018"
TARGET_MONTH = 8
OUTPUT_HTML = "chapter2_usertype_map.html"
# ==============================================

def load_month_data(folder, month):
    frames = []
    for fname in os.listdir(folder):
        if fname.endswith(".csv") and f"2018{month:02d}" in fname:
            path = os.path.join(folder, fname)
            df = pd.read_csv(path)
            df.rename(columns={
                'start station id': 'start_station_id',
                'start station name': 'start_station_name',
                'start station latitude': 'start_lat',
                'start station longitude': 'start_lng',
                'end station id': 'end_station_id',
                'end station name': 'end_station_name',
                'end station latitude': 'end_lat',
                'end station longitude': 'end_lng',
                'usertype': 'usertype'
            }, inplace=True)
            frames.append(df)
    return pd.concat(frames, ignore_index=True)

print(f"正在处理 2018 年 {TARGET_MONTH} 月数据...")
df = load_month_data(DATA_FOLDER, TARGET_MONTH)

# ---------- 起点统计（流出） ----------
start_counts = df.groupby(['start_station_id', 'start_station_name', 'start_lat', 'start_lng', 'usertype']).size().unstack(fill_value=0)
start_counts.reset_index(inplace=True)
start_counts['total'] = start_counts['Subscriber'] + start_counts['Customer']
start_counts['customer_ratio'] = (start_counts['Customer'] / start_counts['total'] * 100).round(2)

start_sites = []
for _, row in start_counts.iterrows():
    start_sites.append({
        'name': row['start_station_name'],
        'lat': float(row['start_lat']),
        'lng': float(row['start_lng']),
        'sub': int(row['Subscriber']),
        'cus': int(row['Customer']),
        'ratio': float(row['customer_ratio'])
    })

# ---------- 终点统计（流入） ----------
end_counts = df.groupby(['end_station_id', 'end_station_name', 'end_lat', 'end_lng', 'usertype']).size().unstack(fill_value=0)
end_counts.reset_index(inplace=True)
end_counts['total'] = end_counts['Subscriber'] + end_counts['Customer']
end_counts['customer_ratio'] = (end_counts['Customer'] / end_counts['total'] * 100).round(2)

end_sites = []
for _, row in end_counts.iterrows():
    end_sites.append({
        'name': row['end_station_name'],
        'lat': float(row['end_lat']),
        'lng': float(row['end_lng']),
        'sub': int(row['Subscriber']),
        'cus': int(row['Customer']),
        'ratio': float(row['customer_ratio'])
    })

data_json = {
    'startSites': start_sites,
    'endSites': end_sites,
    'maxSubStart': int(start_counts['Subscriber'].max()) if start_sites else max(s['sub'] for s in start_sites),
    'maxCusStart': int(start_counts['Customer'].max()) if start_sites else max(s['cus'] for s in start_sites),
    'maxSubEnd': int(end_counts['Subscriber'].max()) if not end_sites else max(s['sub'] for s in end_sites),
    'maxCusEnd': int(end_counts['Customer'].max()) if not end_sites else max(s['cus'] for s in end_sites),
    'centerStart': [float(start_counts['start_lat'].mean()), float(start_counts['start_lng'].mean())],
    'centerEnd': [float(end_counts['end_lat'].mean()), float(end_counts['end_lng'].mean())]
}

# ==================== 生成 HTML（已调整气泡大小） ====================
html_code = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>用户类型分布 · 流出 vs 流入</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: -apple-system, sans-serif; }}
        .maps-container {{
            display: flex;
            width: 100%;
            height: 100vh;
        }}
        .map-panel {{
            flex: 1;
            position: relative;
            border-right: 1px solid #ddd;
        }}
        .map-panel:last-child {{ border-right: none; }}
        .map-panel .map {{ width: 100%; height: 100%; }}

        .control-panel {{
            position: absolute;
            top: 20px;
            left: 20px;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(8px);
            padding: 5px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            width: 160px;
        }}
        select {{
            width: 100%;
            padding: 10px;
            border: none;
            background: transparent;
            font-size: 14px;
            color: #2c3e50;
            cursor: pointer;
            outline: none;
            font-weight: 500;
        }}
        .panel-title {{
            position: absolute;
            top: 20px;
            right: 20px;
            z-index: 1000;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="maps-container">
        <div class="map-panel">
            <div id="mapStart" class="map"></div>
            <div class="panel-title">📤 流出 (起点)</div>
            <div class="control-panel">
                <select id="viewStart">
                    <option value="sub">本地人 Subscriber</option>
                    <option value="cus">游客 Customer</option>
                    <option value="ratio">游客占比 (%)</option>
                </select>
            </div>
        </div>
        <div class="map-panel">
            <div id="mapEnd" class="map"></div>
            <div class="panel-title">📥 流入 (终点)</div>
            <div class="control-panel">
                <select id="viewEnd">
                    <option value="sub">本地人 Subscriber</option>
                    <option value="cus">游客 Customer</option>
                    <option value="ratio">游客占比 (%)</option>
                </select>
            </div>
        </div>
    </div>

    <script>
        const DATA = {json.dumps(data_json, ensure_ascii=False)};

        function createMap(id, center) {{
            const map = L.map(id, {{ zoomControl: false }}).setView(center, 14);
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '&copy; CartoDB'
            }}).addTo(map);
            return map;
        }}

        const mapStart = createMap('mapStart', DATA.centerStart);
        const mapEnd = createMap('mapEnd', DATA.centerEnd);
        const layerStart = L.layerGroup().addTo(mapStart);
        const layerEnd = L.layerGroup().addTo(mapEnd);

        function getColor(value, type, maxes) {{
            if (type === 'ratio') {{
                return value > 50 ? '#e67e22' : 
                       value > 30 ? '#f39c12' : 
                       value > 15 ? '#f1c40f' : '#7f8c8d';
            }}
            const blueScale = ['#ebf5fb', '#85c1e9', '#3498db', '#2874a6', '#1b4f72'];
            const orangeScale = ['#fef5e7', '#f8c471', '#e67e22', '#af601a', '#6e2c00'];
            const scale = type === 'sub' ? blueScale : orangeScale;
            const max = type === 'sub' ? maxes.sub : maxes.cus;
            const idx = Math.min(Math.floor((value / max) * 4), 4);
            return scale[idx];
        }}

        function updateMap(layer, sites, mode, maxes) {{
            layer.clearLayers();
            sites.forEach(site => {{
                let val, radius, color;
                
                if (mode === 'sub') {{
                    val = site.sub;
                    // 调整半径系数，整体缩小：原0.8 -> 0.4
                    radius = Math.sqrt(val) * 0.4;
                    color = getColor(val, 'sub', maxes);
                }} else if (mode === 'cus') {{
                    val = site.cus;
                    // 游客基数小，缩放系数也降低：原1.5 -> 0.8
                    radius = Math.sqrt(val) * 0.8;
                    color = getColor(val, 'cus', maxes);
                }} else {{
                    val = site.ratio;
                    // 占比模式半径：原5 + val/10 -> 4 + val/20
                    radius = 4 + (val / 20);
                    color = getColor(val, 'ratio', maxes);
                }}

                if (val > 0) {{
                    L.circleMarker([site.lat, site.lng], {{
                        radius: radius,
                        fillColor: color,
                        color: '#fff',
                        weight: 1,
                        opacity: 0.8,
                        fillOpacity: 0.7
                    }}).bindPopup(`
                        <b>${{site.name}}</b><br>
                        本地人: ${{site.sub}}<br>
                        游客: ${{site.cus}}<br>
                        游客占比: ${{site.ratio}}%
                    `).addTo(layer);
                }}
            }});
        }}

        const maxesStart = {{ sub: DATA.maxSubStart, cus: DATA.maxCusStart }};
        const maxesEnd = {{ sub: DATA.maxSubEnd, cus: DATA.maxCusEnd }};

        updateMap(layerStart, DATA.startSites, 'sub', maxesStart);
        updateMap(layerEnd, DATA.endSites, 'sub', maxesEnd);

        document.getElementById('viewStart').onchange = (e) => updateMap(layerStart, DATA.startSites, e.target.value, maxesStart);
        document.getElementById('viewEnd').onchange = (e) => updateMap(layerEnd, DATA.endSites, e.target.value, maxesEnd);
    </script>
</body>
</html>'''

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html_code)

print(f"✅ Chapter 2 用户类型分布图（已缩小气泡）已生成：{OUTPUT_HTML}")