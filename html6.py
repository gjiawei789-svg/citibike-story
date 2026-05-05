import pandas as pd
import json
import os

# ==================== 配置 ====================
FILE_PATH = r"E:/data_visual/2018/JC-201808-citibike-tripdata.csv"
OUTPUT_HTML = "chapter5_daily_average_weekend_ratio.html"
# ==============================================

print(f"正在分析日均出行数据: {FILE_PATH}...")
df = pd.read_csv(FILE_PATH, parse_dates=['starttime'])

# 1. 识别日期并区分工作日/周末
df['date'] = df['starttime'].dt.date
df['day_of_week'] = df['starttime'].dt.dayofweek
df['is_weekend'] = df['day_of_week'] >= 5

# 2. 计算 8 月份实际包含的天数
all_days = pd.to_datetime(df['date'].unique())
n_weekend = sum(all_days.dayofweek >= 5)
n_weekday = sum(all_days.dayofweek < 5)

print(f"统计时段内包含: {n_weekday} 个工作日, {n_weekend} 个周末")

def get_daily_average_stats(df, id_col, name_col, lat_col, lng_col):
    """计算日均平均出行量及比率"""
    # 基础分组统计总数
    temp_stats = df.groupby([id_col, name_col, lat_col, lng_col, 'is_weekend']).size().unstack(fill_value=0)
    temp_stats.columns = ['total_weekday', 'total_weekend']
    temp_stats.reset_index(inplace=True)
    
    # --- 核心逻辑修改：计算日均值 ---
    # 工作日日均 = 工作日总数 / 工作日天数
    temp_stats['avg_weekday'] = (temp_stats['total_weekday'] / n_weekday).round(2)
    # 周末日均 = 周末总数 / 周末天数
    temp_stats['avg_weekend'] = (temp_stats['total_weekend'] / n_weekend).round(2)
    
    # 总日均 = 工作日日均 + 周末日均
    temp_stats['total_daily_avg'] = temp_stats['avg_weekday'] + temp_stats['avg_weekend']
    
    # 周末日均比率 = 周末日均 / 总日均
    temp_stats['weekend_avg_ratio'] = (temp_stats['avg_weekend'] / temp_stats['total_daily_avg'] * 100).round(1)
    
    res = []
    for _, row in temp_stats.iterrows():
        if row['total_daily_avg'] > 0:
            res.append({
                'name': row[name_col],
                'lat': float(row[lat_col]),
                'lng': float(row[lng_col]),
                'total_avg': float(row['total_daily_avg']),
                'avg_weekday': float(row['avg_weekday']),
                'avg_weekend': float(row['avg_weekend']),
                'ratio': float(row['weekend_avg_ratio'])
            })
    return res

# 分别计算出发和到达的日均统计[cite: 1]
start_stats = get_daily_average_stats(df, 'start station id', 'start station name', 'start station latitude', 'start station longitude')
end_stats = get_daily_average_stats(df, 'end station id', 'end station name', 'end station latitude', 'end station longitude')

data_json = {
    'start_stats': start_stats,
    'end_stats': end_stats,
    'center': [df['start station latitude'].mean(), df['start station longitude'].mean()]
}

# ==================== 生成 HTML ====================
html_code = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>周末日均出行比率可视化</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: -apple-system, sans-serif; background: #f4f7f9; }}
        #map {{ width: 100%; height: 100vh; }}
        
        .selector-panel {{
            position: absolute; top: 20px; left: 20px; z-index: 1000;
            background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(10px);
            padding: 12px 20px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            border: 1px solid rgba(0,0,0,0.05);
        }}
        select {{ padding: 8px 12px; border-radius: 8px; border: 1px solid #ddd; cursor: pointer; }}

        .custom-tooltip {{
            background: #fff9c4 !important; border: 1px solid #fbc02d !important;
            padding: 10px; font-size: 13px !important; box-shadow: 2px 4px 12px rgba(0,0,0,0.15);
        }}
        
        .legend {{
            position: absolute; bottom: 30px; right: 20px; z-index: 1000;
            background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 15px rgba(0,0,0,0.1);
        }}
        .legend-gradient {{
            width: 20px; height: 150px;
            background: linear-gradient(to top, #d32f2f, #fbc02d, #388e3c);
            margin: 8px auto; border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="selector-panel">
        <label style="font-weight:bold; color:#2c3e50; margin-right:8px;">分析维度:</label>
        <select id="typeSelect">
            <option value="start_stats">🚴 出发站日均 (Daily Avg Starts)</option>
            <option value="end_stats">🏁 到达站日均 (Daily Avg Ends)</option>
        </select>
    </div>
    <div class="legend">
        <div style="text-align:center; font-weight:bold; font-size:12px;">周末日均占比 %</div>
        <div style="text-align:center; font-size:11px; color:#666;">100% (休闲)</div>
        <div class="legend-gradient"></div>
        <div style="text-align:center; font-size:11px; color:#666;">0% (通勤)</div>
    </div>

    <script>
        const DATA = {json.dumps(data_json, ensure_ascii=False)};
        const map = L.map('map', {{ zoomControl: false }}).setView(DATA.center, 14);
        
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);

        function getColor(ratio) {{
            return ratio > 65 ? '#388e3c' : 
                   ratio > 50 ? '#8bc34a' :
                   ratio > 35 ? '#fbc02d' :
                   ratio > 20 ? '#f57c00' : '#d32f2f';
        }}

        let layer = L.layerGroup().addTo(map);

        function update(type) {{
            layer.clearLayers();
            DATA[type].forEach(s => {{
                // 气泡大小代表“日均总出行量”，缩放系数调小至 1.0 避免遮挡[cite: 1]
                const radius = Math.sqrt(s.total_avg) * 3; 
                
                L.circleMarker([s.lat, s.lng], {{
                    radius: radius,
                    fillColor: getColor(s.ratio),
                    color: '#fff',
                    weight: 1,
                    fillOpacity: 0.8
                }}).addTo(layer).bindTooltip(`
                    <div style="line-height:1.6">
                        <b style="font-size:14px; color:#1a252f;">${{s.name}}</b><br>
                        <hr style="border:0; border-top:1px solid #ddd; margin:5px 0;">
                        <b>日均总出行:</b> ${{s.total_avg.toFixed(2)}} 次/天<br>
                        <b>工作日日均:</b> ${{s.avg_weekday.toFixed(2)}} 次/天<br>
                        <b>周末日均:</b> ${{s.avg_weekend.toFixed(2)}} 次/天<br>
                        <b style="color:#e67e22;">周末日均占比:</b> ${{s.ratio}}%
                    </div>
                `, {{ className: 'custom-tooltip', sticky: true }});
            }});
        }}

        document.getElementById('typeSelect').onchange = (e) => update(e.target.value);
        update('start_stats');
    </script>
</body>
</html>'''

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html_code)

print(f"✅ 日均分析图已生成：{OUTPUT_HTML}")