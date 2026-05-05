import pandas as pd
import os
import json
import math

# ==================== 配置 ====================
DATA_FOLDER = r"E:\data_visual\2018"
TARGET_MONTH = 8  # 8月
OUTPUT_HTML = "chapter1_station_heatmap.html"
# ==============================================

def load_month_data(folder, month):
    """只读取指定月份的 CSV 文件"""
    frames = []
    for fname in os.listdir(folder):
        if fname.endswith(".csv"):
            if f"2018{month:02d}" in fname:
                path = os.path.join(folder, fname)
                df = pd.read_csv(path, parse_dates=['starttime', 'stoptime'])
                df.rename(columns={
                    'start station id': 'start_station_id',
                    'start station name': 'start_station_name',
                    'start station latitude': 'start_lat',
                    'start station longitude': 'start_lng',
                    'end station id': 'end_station_id',
                    'end station name': 'end_station_name',
                    'end station latitude': 'end_lat',
                    'end station longitude': 'end_lng'
                }, inplace=True)
                frames.append(df)
    if not frames:
        raise FileNotFoundError(f"未找到 2018 年 {month} 月的数据文件")
    return pd.concat(frames, ignore_index=True)

print(f"正在读取 2018 年 {TARGET_MONTH} 月数据...")
df = load_month_data(DATA_FOLDER, TARGET_MONTH)

# ---------- 统计站点出发 / 到达次数 ----------
start_counts = df.groupby(['start_station_id', 'start_station_name', 'start_lat', 'start_lng']).size().reset_index(name='count')
start_counts = start_counts.rename(columns={'start_station_id': 'id', 'start_station_name': 'name', 'start_lat': 'lat', 'start_lng': 'lng'})

end_counts = df.groupby(['end_station_id', 'end_station_name', 'end_lat', 'end_lng']).size().reset_index(name='count')
end_counts = end_counts.rename(columns={'end_station_id': 'id', 'end_station_name': 'name', 'end_lat': 'lat', 'end_lng': 'lng'})

def build_site_list(df):
    sites = []
    for _, row in df.iterrows():
        sites.append({
            'id': str(row['id']),
            'name': row['name'],
            'lat': float(row['lat']),
            'lng': float(row['lng']),
            'count': int(row['count'])
        })
    return sites

start_sites = build_site_list(start_counts)
end_sites = build_site_list(end_counts)

all_lats = [s['lat'] for s in start_sites + end_sites]
all_lngs = [s['lng'] for s in start_sites + end_sites]

data_json = {
    'startSites': start_sites,
    'endSites': end_sites,
    'maxStart': max(s['count'] for s in start_sites) if start_sites else 1,
    'maxEnd': max(s['count'] for s in end_sites) if end_sites else 1,
    'centerLat': sum(all_lats) / len(all_lats),
    'centerLng': sum(all_lngs) / len(all_lngs)
}

# ==================== 生成符合模板风格的 HTML ====================
html_code = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>站点热度分布</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: -apple-system, sans-serif; }}
        #map {{ width: 100%; height: 100vh; background: #f8f9fa; }}
        
        /* 匹配模板的交互组件样式 */
        .selector-panel {{
            position: absolute;
            top: 20px;
            right: 20px;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(10px);
            padding: 12px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border: 1px solid rgba(0,0,0,0.05);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .selector-panel label {{
            font-size: 13px;
            font-weight: 600;
            color: #2c3e50;
        }}
        select {{
            padding: 6px 12px;
            border-radius: 8px;
            border: 1px solid #ddd;
            outline: none;
            cursor: pointer;
            font-size: 13px;
            color: #546e7a;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="selector-panel">
        <label>数据维度</label>
        <select id="typeSelect">
            <option value="start">🚴 出发频次 (Starts)</option>
            <option value="end">🏁 到达频次 (Ends)</option>
        </select>
    </div>

    <script>
        const DATA = {json.dumps(data_json, ensure_ascii=False)};

        const map = L.map('map', {{ zoomControl: false }}).setView([DATA.centerLat, DATA.centerLng], 14);
        L.control.zoom({{ position: 'bottomright' }}).addTo(map);

        // 使用干净的底图
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; OpenStreetMap'
        }}).addTo(map);

        // 模仿图片中的 Plasma 配色方案 (深紫 -> 红 -> 橙 -> 黄)
        function getStyle(count, max) {{
            const ratio = Math.min(count / max, 1);
            const colors = [
                '#0d0887', '#46039f', '#7201a8', '#9c179e', 
                '#bd3786', '#d8576b', '#ed7953', '#fb9f3a', '#fdca26', '#f0f921'
            ];
            const idx = Math.floor(ratio * (colors.length - 1));
            return {{
                fillColor: colors[idx],
                radius: 6 + 24 * Math.sqrt(ratio), // 同样使用开方缩放增大差异
                fillOpacity: 0.75,
                color: '#fff',
                weight: 1
            }};
        }}

        let layer = L.layerGroup().addTo(map);

        function update(type) {{
            layer.clearLayers();
            const sites = type === 'start' ? DATA.startSites : DATA.endSites;
            const max = type === 'start' ? DATA.maxStart : DATA.maxEnd;

            sites.forEach(s => {{
                const style = getStyle(s.count, max);
                L.circleMarker([s.lat, s.lng], style)
                    .bindPopup(`<b>${{s.name}}</b><br>频次: ${{s.count.toLocaleString()}}`)
                    .addTo(layer);
            }});
        }}

        document.getElementById('typeSelect').onchange = (e) => update(e.target.value);
        update('start');
    </script>
</body>
</html>'''

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html_code)

print(f"✅ 已生成符合模板风格的地图：{OUTPUT_HTML}")