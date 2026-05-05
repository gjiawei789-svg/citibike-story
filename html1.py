import pandas as pd
import os
import json

DATA_FOLDER = r"E:\data_visual\2018"
OUTPUT_HTML = "chapter0_user_type_monthly.html"

def load_all_data(folder):
    frames = []
    for fname in os.listdir(folder):
        if fname.endswith(".csv"):
            path = os.path.join(folder, fname)
            df = pd.read_csv(path, parse_dates=['starttime', 'stoptime'])
            df.rename(columns={'usertype': 'usertype'}, inplace=True)
            df['month'] = df['starttime'].dt.month
            frames.append(df)
    return pd.concat(frames, ignore_index=True)

print("读取数据...")
df = load_all_data(DATA_FOLDER)

user_monthly = df.groupby(['month', 'usertype']).size().unstack(fill_value=0)
if 'Subscriber' not in user_monthly.columns:
    user_monthly['Subscriber'] = 0
if 'Customer' not in user_monthly.columns:
    user_monthly['Customer'] = 0

monthly_subscribers = [int(user_monthly.loc[m, 'Subscriber']) if m in user_monthly.index else 0 for m in range(1,13)]
monthly_customers = [int(user_monthly.loc[m, 'Customer']) if m in user_monthly.index else 0 for m in range(1,13)]
total_subscribers = sum(monthly_subscribers)
total_customers = sum(monthly_customers)

data_json = json.dumps({
    'monthly_subscribers': monthly_subscribers,
    'monthly_customers': monthly_customers,
    'total_subscribers': total_subscribers,
    'total_customers': total_customers
})

html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>会员/非会员月度骑行分析</title>
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
        .dashboard {{
            display: flex;
            flex-wrap: wrap;
            width: 100%;
            height: 100%;
        }}
        .chart-container {{
            flex: 1;
            min-width: 0;
            height: 100%;
            background: #fff;
            border-radius: 14px;
            box-shadow: 0 4px 18px rgba(0,0,0,0.06);
            padding: 20px;
            display: flex;
            flex-direction: column;
        }}
        h2 {{
            text-align: center;
            color: #2c3e50;
            margin: 0 0 10px 0;
            font-weight: 600;
            flex-shrink: 0;
        }}
        .chart {{
            width: 100%;
            flex: 1;
            min-height: 0;
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="chart-container">
            <h2>👥 每月会员 / 非会员骑行量</h2>
            <div id="barChart" class="chart"></div>
        </div>
        <div class="chart-container">
            <h2>🥧 会员 / 非会员占比</h2>
            <div id="pieChart" class="chart"></div>
        </div>
    </div>

    <script>
        const DATA = {data_json};
        const months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];

        const barChart = echarts.init(document.getElementById('barChart'));
        const pieChart = echarts.init(document.getElementById('pieChart'));

        let selectedMonth = null;

        function renderBarChart(highlightMonth = null) {{
            barChart.setOption({{
                tooltip: {{
                    trigger: 'axis',
                    axisPointer: {{ type: 'shadow' }}
                }},
                legend: {{
                    data: ['Subscriber', 'Customer'],
                    top: 0
                }},
                grid: {{
                    left: '15%',
                    right: '5%',
                    top: 50,
                    bottom: 30
                }},
                xAxis: {{
                    type: 'category',
                    data: months,
                    axisLabel: {{ rotate: 0, fontSize: 12 }}
                }},
                yAxis: {{
                    type: 'value',
                    name: '骑行次数'
                }},
                series: [
                    {{
                        name: 'Subscriber',
                        type: 'bar',
                        stack: 'total',
                        data: DATA.monthly_subscribers,
                        color: '#3498db',
                        label: {{
                            show: true,
                            position: 'inside',
                            formatter: p => p.value.toLocaleString()
                        }},
                        emphasis: {{ focus: 'series' }}
                    }},
                    {{
                        name: 'Customer',
                        type: 'bar',
                        stack: 'total',
                        data: DATA.monthly_customers,
                        color: '#f39c12',
                        label: {{
                            show: true,
                            position: 'inside',
                            formatter: p => p.value.toLocaleString()
                        }},
                        emphasis: {{ focus: 'series' }}
                    }}
                ]
            }});

            if (highlightMonth !== null) {{
                barChart.dispatchAction({{ type: 'highlight', seriesIndex: 0, dataIndex: highlightMonth }});
                barChart.dispatchAction({{ type: 'highlight', seriesIndex: 1, dataIndex: highlightMonth }});
            }} else {{
                barChart.dispatchAction({{ type: 'downplay' }});
            }}
        }}

        function renderPieChart(subscriberCount, customerCount) {{
            pieChart.setOption({{
                tooltip: {{ trigger: 'item' }},
                legend: {{
                    orient: 'horizontal',
                    left: 'center',
                    top: 0,
                    textStyle: {{ fontSize: 14 }}
                }},
                series: [{{
                    type: 'pie',
                    radius: ['45%', '75%'],
                    center: ['50%', '55%'],
                    data: [
                        {{ value: subscriberCount, name: 'Subscriber', itemStyle: {{ color: '#3498db' }} }},
                        {{ value: customerCount, name: 'Customer', itemStyle: {{ color: '#f39c12' }} }}
                    ],
                    label: {{
                        formatter: '{{b}}: {{c}} ({{d}}%)',
                        fontSize: 14
                    }}
                }}]
            }});
        }}

        barChart.on('click', function(params) {{
            if (params.componentType === 'series') {{
                const monthIndex = params.dataIndex;
                if (selectedMonth === monthIndex) {{
                    selectedMonth = null;
                    renderBarChart(null);
                    renderPieChart(DATA.total_subscribers, DATA.total_customers);
                }} else {{
                    selectedMonth = monthIndex;
                    renderBarChart(monthIndex);
                    renderPieChart(DATA.monthly_subscribers[monthIndex], DATA.monthly_customers[monthIndex]);
                }}
            }}
        }});

        barChart.getZr().on('click', function(params) {{
            if (!params.target) {{
                selectedMonth = null;
                renderBarChart(null);
                renderPieChart(DATA.total_subscribers, DATA.total_customers);
            }}
        }});

        renderBarChart(null);
        renderPieChart(DATA.total_subscribers, DATA.total_customers);

        window.addEventListener('resize', () => {{
            barChart.resize();
            pieChart.resize();
        }});
    </script>
</body>
</html>'''

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html_template)
print(f"✅ 已生成 {OUTPUT_HTML}")