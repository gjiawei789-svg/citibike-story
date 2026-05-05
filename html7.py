import pandas as pd
import json
import os

# ==================== 配置 ====================
FILE_PATH = r"E:/data_visual/2018/JC-201808-citibike-tripdata.csv"
OUTPUT_HTML = "chapter6_od_curves.html"
TOP_N = 20
# ==============================================

print("正在读取并预处理数据...")
df = pd.read_csv(FILE_PATH, parse_dates=['starttime'])
df['date'] = df['starttime'].dt.date
df['weekday'] = df['starttime'].dt.dayofweek  # 0 = 周一，6 = 周日
df['is_weekend'] = df['weekday'] >= 5

def get_top_routes(sub_df):
    """给定 DataFrame 子集，返回 Top N OD 路线"""
    od = sub_df.groupby([
        'start station id', 'start station name', 'start station latitude', 'start station longitude',
        'end station id', 'end station name', 'end station latitude', 'end station longitude'
    ]).size().reset_index(name='count')
    top = od.nlargest(TOP_N, 'count')
    routes = []
    for _, row in top.iterrows():
        routes.append({
            'start': {
                'name': row['start station name'],
                'lat': float(row['start station latitude']),
                'lng': float(row['start station longitude'])
            },
            'end': {
                'name': row['end station name'],
                'lat': float(row['end station latitude']),
                'lng': float(row['end station longitude'])
            },
            'count': int(row['count'])
        })
    return routes

# 生成三种数据
routes_all = get_top_routes(df)
routes_weekday = get_top_routes(df[~df['is_weekend']])
routes_weekend = get_top_routes(df[df['is_weekend']])

# 全局最大值（用于颜色和粗细统一映射）
max_all = max((r['count'] for r in routes_all), default=0)
max_weekday = max((r['count'] for r in routes_weekday), default=0)
max_weekend = max((r['count'] for r in routes_weekend), default=0)
global_max = max(max_all, max_weekday, max_weekend)

center = [df['start station latitude'].mean(), df['start station longitude'].mean()]

data = json.dumps({
    'routesAll': routes_all,
    'routesWeekday': routes_weekday,
    'routesWeekend': routes_weekend,
    'maxCount': float(global_max),
    'center': center
})

html_code = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Top 20 热门骑行曲线 (工作日 / 周末)</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/gh/elfalem/Leaflet.curve/leaflet.curve.js"></script>
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ width: 100%; height: 100vh; }}
        .control-panel {{
            position: absolute;
            top: 20px;
            left: 20px;
            z-index: 1000;
            background: rgba(255,255,255,0.9);
            backdrop-filter: blur(8px);
            padding: 8px 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }}
        select {{
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid #ccc;
        }}
        .legend {{
            position: absolute;
            bottom: 30px;
            right: 20px;
            z-index: 1000;
            background: white;
            padding: 12px;
            border-radius: 8px;
            font-size: 13px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}
        .legend span {{
            display: inline-block;
            vertical-align: middle;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="control-panel">
        <label for="modeSelect"><strong>📅 显示模式：</strong></label>
        <select id="modeSelect">
            <option value="all">全部 (All Days)</option>
            <option value="weekday">工作日 (Weekdays)</option>
            <option value="weekend">周末 (Weekends)</option>
        </select>
    </div>
    <div class="legend">
        <strong>Top 20 热门路线</strong><br>
        <span style="background: lightblue; width: 12px; height: 12px; border-radius: 50%;"></span> 起点 &nbsp;
        <span style="background: lightpink; width: 12px; height: 12px; border-radius: 50%;"></span> 终点<br>
        <div style="margin-top:6px; height: 10px; width: 120px; background: linear-gradient(to right, #c994c7, #980043);"></div>
        <div style="display: flex; justify-content: space-between; width: 120px;"><span>低</span><span>高</span></div>
    </div>

    <script>
        const DATA = {data};
        const map = L.map('map').setView(DATA.center, 14);

        // 白色底图
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; CartoDB',
            maxZoom: 18
        }}).addTo(map);

        // 颜色映射（基于全局最大值统一）
        function getCurveColor(count) {{
            const ratio = count / DATA.maxCount;
            const start = [201, 148, 199]; // #c994c7
            const end = [152, 0, 67];      // #980043
            const r = Math.round(start[0] + ratio * (end[0] - start[0]));
            const g = Math.round(start[1] + ratio * (end[1] - start[1]));
            const b = Math.round(start[2] + ratio * (end[2] - start[2]));
            return `rgb(${{r}},${{g}},${{b}})`;
        }}

        function getWeight(count) {{
            return 2 + (count / DATA.maxCount) * 8;
        }}

        let currentCurvesLayer = L.layerGroup().addTo(map);
        let currentPointsLayer = L.layerGroup().addTo(map);

        function renderRoutes(routes) {{
            currentCurvesLayer.clearLayers();
            currentPointsLayer.clearLayers();

            const startSet = new Set();
            const endSet = new Set();

            routes.forEach(route => {{
                const s = [route.start.lat, route.start.lng];
                const e = [route.end.lat, route.end.lng];
                const offsetX = (e[0] - s[0]) * 0.2;
                const offsetY = (e[1] - s[1]) * 0.2;
                const mid = [
                    (s[0] + e[0]) / 2 + offsetY,
                    (s[1] + e[1]) / 2 - offsetX
                ];
                const path = ['M', s, 'Q', mid, e];

                L.curve(path, {{
                    color: getCurveColor(route.count),
                    weight: getWeight(route.count),
                    opacity: 0.7,
                    fill: false
                }}).bindPopup(
                    `<b>${{route.start.name}}</b> → <b>${{route.end.name}}</b><br>出行量: ${{route.count.toLocaleString()}} 次`
                ).addTo(currentCurvesLayer);

                // 起点
                const sKey = s[0].toFixed(5) + ',' + s[1].toFixed(5);
                if (!startSet.has(sKey)) {{
                    startSet.add(sKey);
                    L.circleMarker(s, {{
                        radius: 5,
                        fillColor: 'lightblue',
                        color: 'white',
                        weight: 1,
                        fillOpacity: 0.9
                    }}).bindPopup('起点: ' + route.start.name).addTo(currentPointsLayer);
                }}
                // 终点
                const eKey = e[0].toFixed(5) + ',' + e[1].toFixed(5);
                if (!endSet.has(eKey)) {{
                    endSet.add(eKey);
                    L.circleMarker(e, {{
                        radius: 5,
                        fillColor: 'lightpink',
                        color: 'white',
                        weight: 1,
                        fillOpacity: 0.9
                    }}).bindPopup('终点: ' + route.end.name).addTo(currentPointsLayer);
                }}
            }});
        }}

        // 初始加载全部
        renderRoutes(DATA.routesAll);

        // 切换事件
        document.getElementById('modeSelect').addEventListener('change', function(e) {{
            const mode = e.target.value;
            if (mode === 'all') renderRoutes(DATA.routesAll);
            else if (mode === 'weekday') renderRoutes(DATA.routesWeekday);
            else if (mode === 'weekend') renderRoutes(DATA.routesWeekend);
        }});
    </script>
</body>
</html>'''

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html_code)

print(f"✅ 已生成文件：{OUTPUT_HTML}，包含白色底图和工作日/周末切换功能。")