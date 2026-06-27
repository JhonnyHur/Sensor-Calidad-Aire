from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json
import os
#import firebase_admin
#from firebase_admin import credentials, firestore

# # Inicializar Firebase solo una vez
# if not firebase_admin._apps:
#     cred = credentials.Certificate("firebase_key.json")
#     firebase_admin.initialize_app(cred)
#     db = firestore.client()

app = Flask(__name__)

# Datos históricos
sensor_data = {
    'last_update': None,
    'current': {},
    'history': []
}

@app.route('/')
def index():
    return render_template('index.html', data=sensor_data)

@app.route('/data', methods=['POST'])
def receive_data():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Request must be JSON'}), 400

    try:
        data = request.get_json()
        required_fields = ['pm1_0', 'pm2_5', 'temperature', 'humidity']
        for field in required_fields:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400

        # ✅ Usar timestamp del ESP si está disponible
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        sensor_data['current'] = data
        sensor_data['last_update'] = data['timestamp']
        sensor_data['history'].append(data)
        if len(sensor_data['history']) > 100:
            sensor_data['history'] = sensor_data['history'][-100:]

        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/mapa')
def mostrar_mapa():
    # Obtener el último dato de PM2.5
    pm25 = sensor_data['current'].get('pm2_5', 0) if sensor_data['current'] else 0
    lat, lon = 3.452065680855233, -76.53538487798981

    # Determinar color según rangos de calidad del aire
    def determinar_color(pm25):
        if pm25 <= 12:
            return 'green'
        elif pm25 <= 35:
            return 'yellow'
        elif pm25 <= 55:
            return 'orange'
        else:
            return 'red'
    
    color = determinar_color(pm25)

    # Extraer últimos 20 registros para el gráfico
    ultimos = sensor_data['history'][-20:]  # puedes ajustar el número
    labels = [d.get("timestamp", "N/A") for d in ultimos]
    valores_pm25 = [d.get("pm2_5", 0) for d in ultimos]

    return render_template(
        'mapa.html',
        lat=lat,
        lon=lon,
        color=color,
        pm25=pm25,
        labels=labels,
        valores_pm25=valores_pm25
    )

@app.route('/dashboard')
def dashboard():
    # Enviar los últimos 20 registros históricos
    history = sensor_data['history'][-20:]  # Puedes ajustar a más si quieres
    return render_template('dashboard.html', history=history)


@app.route('/api/data')
def get_data():
    return jsonify(sensor_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)