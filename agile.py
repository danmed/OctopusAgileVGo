import requests
from datetime import datetime, timedelta
import pytz
import json

def get_agile_prices(product_code, tariff_code, days=2):
    today = datetime.now(pytz.UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = today + timedelta(days=days)
    
    url = f"https://api.octopus.energy/v1/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/"
    params = {
        'period_from': today.isoformat(),
        'period_to': end_date.isoformat()
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Error fetching Agile prices: {response.status_code}")
        print(f"Response: {response.text}")
        return []
    return response.json()['results']

def get_go_price(product_code, tariff_code):
    url = f"https://api.octopus.energy/v1/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Error fetching Go prices: {response.status_code}")
        print(f"Response: {response.text}")
        return {'day': 0, 'night': 0}
    
    data = response.json()
    
    if 'results' in data:
        rates = data['results']
    elif isinstance(data, list):
        rates = data
    else:
        print("Unexpected API response structure. Please check the API documentation for changes.")
        return {'day': 0, 'night': 0}
    
    go_prices = {}
    for rate in rates:
        if 'valid_from' in rate and 'value_inc_vat' in rate:
            time = datetime.fromisoformat(rate['valid_from']).time()
            if time >= datetime.strptime("00:30", "%H:%M").time() and time < datetime.strptime("04:30", "%H:%M").time():
                go_prices['night'] = round(rate['value_inc_vat'], 2)
            else:
                go_prices['day'] = round(rate['value_inc_vat'], 2)
    
    if 'day' not in go_prices or 'night' not in go_prices:
        print("Unable to determine day and night rates from the API response.")
        return {'day': 0, 'night': 0}
    
    return go_prices

def create_html_table(agile_prices, go_prices):
    html = """
    <style>
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid black; padding: 8px; text-align: left; }
        .green { background-color: #90EE90; }
        .red { background-color: #FFB6C1; }
        .current { background-color: #E6E6FA; }
        .date-header { background-color: #f2f2f2; font-weight: bold; }
    </style>
    """
    
    now = datetime.now(pytz.UTC)
    current_period = now.replace(minute=0 if now.minute < 30 else 30, second=0, microsecond=0)
    
    # Group prices by date
    prices_by_date = {}
    for price in agile_prices:
        date = datetime.fromisoformat(price['valid_from']).date()
        if date not in prices_by_date:
            prices_by_date[date] = []
        prices_by_date[date].append(price)
    
    # Sort dates with today first
    sorted_dates = sorted(prices_by_date.keys(), key=lambda x: abs((x - now.date()).days))
    
    for date in sorted_dates:
        prices = prices_by_date[date]
        html += f"<h2>{date.strftime('%A, %d %B %Y')}</h2>"
        html += """
        <table>
        <tr><th>Time Period</th><th>Agile Price (p/kWh)</th><th>Go Price (p/kWh)</th></tr>
        """
        
        for price in reversed(prices):
            time = datetime.fromisoformat(price['valid_from'])
            time_str = time.strftime('%H:%M')
            agile_value = round(price['value_inc_vat'], 2)
            
            # Determine Go price based on time
            if '00:30' <= time_str < '04:30':
                go_value = go_prices['night']
            else:
                go_value = go_prices['day']
            
            agile_class = ''
            if agile_value < 15:
                agile_class = 'green'
            elif agile_value > 25:
                agile_class = 'red'
            
            row_class = 'current' if time == current_period else ''
            
            html += f"""<tr class='{row_class}'>
                <td>{time_str}</td>
                <td class='{agile_class}'>{agile_value}</td>
                <td>{go_value}</td>
            </tr>"""
        
        html += "</table>"
    
    return html

# Replace these with your actual tariff details
#agile_product_code = "AGILE-FLEX-22-11-25"
#agile_tariff_code = "E-1R-AGILE-FLEX-22-11-25-M"
#go_product_code = "GO-VAR-22-10-01"
#go_tariff_code = "E-1R-GO-VAR-22-10-01-M"

agile_product_code = "AGILE-18-02-21"
agile_tariff_code = "E-1R-AGILE-18-02-21-C"
go_product_code = "GO-VAR-BB-23-02-07"
go_tariff_code = "E-1R-GO-VAR-BB-23-02-07-A"

agile_prices = get_agile_prices(agile_product_code, agile_tariff_code, days=2)
go_prices = get_go_price(go_product_code, go_tariff_code)
table_html = create_html_table(agile_prices, go_prices)

with open('octopus_prices.html', 'w') as f:
    f.write(f"<html><body><h1>Octopus Agile and Go Prices</h1>{table_html}</body></html>")

print("HTML file 'octopus_prices.html' has been created with Agile and Go prices for today and tomorrow.")
