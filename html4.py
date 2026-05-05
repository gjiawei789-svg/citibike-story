import pandas as pd
import requests
import json
import os

YEAR = 2018
DATA_FOLDER = r"E:\data_visual\2018"
OUTPUT_WEATHER_CSV = "nyc_weather_2018.csv"
OUTPUT_HTML = "chapter3_weather_calendar.html"

def fetch_nyc_weather(year):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "daily": ["temperature_2m_mean", "precipitation_sum",
                  "relative_humidity_2m_mean", "wind_speed_10m_max"],
        "timezone": "America/New_York"
    }
    r = requests.get(url, params=params)
    data = r.json()['daily']
    df = pd.DataFrame({
        'date': pd.to_datetime(data['time']),
        'temp_mean': data['temperature_2m_mean'],
        'precip_sum': data['precipitation_sum'],
        'humidity_mean': data['relative_humidity_2m_mean'],
        'wind_max': data['wind_speed_10m_max']
    })
    df['temp_f'] = df['temp_mean'] * 9/5 + 32
    return df

print("获取天气数据...")
weather = fetch_nyc_weather(YEAR)
weather.to_csv(OUTPUT_WEATHER_CSV, index=False)

weather['month'] = weather['date'].dt.month
monthly_weather = weather.groupby('month').agg(
    avg_temp=('temp_f', 'mean'),
    total_precip=('precip_sum', 'sum'),
    avg_humidity=('humidity_mean', 'mean'),
    avg_wind=('wind_max', 'mean')
).reset_index()

def load_rides(folder):
    frames = []
    for fname in os.listdir(folder):
        if fname.endswith(".csv") and str(YEAR) in fname:
            path = os.path.join(folder, fname)
            df = pd.read_csv(path, parse_dates=['starttime'])
            df['month'] = df['starttime'].dt.month
            frames.append(df)
    return pd.concat(frames, ignore_index=True)

print("读取骑行数据...")
rides = load_rides(DATA_FOLDER)
monthly_rides = rides.groupby('month').size().reset_index(name='rides')

merged = monthly_weather.merge(monthly_rides, on='month', how='left')
merged['rides'] = merged['rides'].fillna(0).astype(int)

months_list = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']
data_dict = {
    "months": months_list,
    "rides": [int(merged[merged['month']==m+1]['rides'].values[0]) if not merged[merged['month']==m+1].empty else 0 for m in range(12)],
    "temp": [round(merged[merged['month']==m+1]['avg_temp'].values[0],1) if not merged[merged['month']==m+1].empty else None for m in range(12)],
    "precip": [round(merged[merged['month']==m+1]['total_precip'].values[0],1) if not merged[merged['month']==m+1].empty else None for m in range(12)],
    "humidity": [round(merged[merged['month']==m+1]['avg_humidity'].values[0],1) if not merged[merged['month']==m+1].empty else None for m in range(12)],
    "wind": [round(merged[merged['month']==m+1]['avg_wind'].values[0],1) if not merged[merged['month']==m+1].empty else None for m in range(12)]
}

html_code = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>天气与骑行日历</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            margin: 0;
            padding: 0;
            background: #f5f7fa;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            overflow: hidden;
            height: 100vh;
        }}
        .chart-container {{
            width: 100%;
            height: 100%;
            background: white;
            border-radius: 14px;
            box-shadow: 0 4px 18px rgba(0,0,0,0.06);
            padding: 20px;
            display: flex;
            flex-direction: column;
            position: relative;
        }}
        h2 {{
            text-align: center;
            color: #2c3e50;
            margin: 0 0 10px 0;
            flex-shrink: 0;
        }}
        .control {{
            position: absolute;
            top: 20px;
            right: 30px;
            display: flex;
            align-items: center;
            gap: 8px;
            z-index: 10;
        }}
        select {{
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid #ccc;
            font-size: 14px;
        }}
        #mainChart {{
            width: 100%;
            flex: 1;
            min-height: 0;
        }}
    </style>
</head>
<body>
    <div class="chart-container">
        <h2>🌤️ 每月骑行量与天气指标</h2>
        <div class="control">
            <label for="metricSelect">对比指标：</label>
            <select id="metricSelect">
                <option value="precip">降水 (mm)</option>
                <option value="humidity">湿度 (%)</option>
                <option value="wind">风速 (km/h)</option>
            </select>
        </div>
        <div id="mainChart"></div>
    </div>

    <script>
        const DATA = {json.dumps(data_dict, ensure_ascii=False)};
        const chart = echarts.init(document.getElementById('mainChart'));

        const metricNames = {{
            precip: '降水 (mm)',
            humidity: '湿度 (%)',
            wind: '风速 (km/h)'
        }};

        function renderChart(metric) {{
            const option = {{
                tooltip: {{
                    trigger: 'axis',
                    axisPointer: {{ type: 'cross' }}
                }},
                legend: {{
                    data: ['骑行量', '平均温度 (°F)', metricNames[metric]],
                    top: 0
                }},
                grid: {{
                    left: '8%',
                    right: '8%',
                    top: 50,
                    bottom: 30
                }},
                xAxis: {{
                    type: 'category',
                    data: DATA.months,
                    axisLabel: {{ rotate: 0 }}
                }},
                yAxis: [
                    {{
                        type: 'value',
                        name: '骑行次数',
                        axisLabel: {{ formatter: val => val.toLocaleString() }}
                    }},
                    {{
                        type: 'value',
                        name: '温度 / 气候指标',
                        axisLabel: {{ formatter: '{{value}}' }}
                    }}
                ],
                series: [
                    {{
                        name: '骑行量',
                        type: 'bar',
                        data: DATA.rides,
                        yAxisIndex: 0,
                        color: '#3498db',
                        label: {{
                            show: true,
                            position: 'top',
                            formatter: p => p.value.toLocaleString(),
                            fontSize: 10
                        }}
                    }},
                    {{
                        name: '平均温度 (°F)',
                        type: 'line',
                        data: DATA.temp,
                        yAxisIndex: 1,
                        color: '#e74c3c',
                        lineStyle: {{ width: 3 }},
                        symbol: 'circle',
                        symbolSize: 8,
                        label: {{ show: false }}
                    }},
                    {{
                        name: metricNames[metric],
                        type: 'line',
                        data: DATA[metric],
                        yAxisIndex: 1,
                        color: '#27ae60',
                        lineStyle: {{ width: 2, type: 'dashed' }},
                        symbol: 'diamond',
                        symbolSize: 7,
                        label: {{ show: false }}
                    }}
                ]
            }};
            chart.setOption(option, true);
        }}

        renderChart('precip');

        document.getElementById('metricSelect').addEventListener('change', function(e) {{
            renderChart(e.target.value);
        }});

        window.addEventListener('resize', () => chart.resize());
    </script>
</body>
</html>'''

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html_code)

print(f"✅ 已生成 {OUTPUT_HTML}")