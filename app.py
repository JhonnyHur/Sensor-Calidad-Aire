from flask import Flask, render_template, request, jsonify
from datetime import datetime
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os

# ─── Conexión a MongoDB Atlas ───────────────────────────────────────────────
MONGO_URI = os.environ.get("MONGO_URI")

client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
db = client["calidad_aire"]
collection = db["mediciones"]

app = Flask(__name__)


# ─── Caché en memoria (últimos 100 registros para el dashboard) ──────────────
sensor_data = {
    'last_update': None,
    'current': {},
    'history': []
}

# ─── Cargar historial previo desde MongoDB al arrancar ─
ultimos = list(collection.find({}, {'_id': 0}).sort('timestamp', -1).limit(100))
sensor_data['history'] = list(reversed(ultimos))
if sensor_data['history']:
    sensor_data['current'] = sensor_data['history'][-1]
    sensor_data['last_update'] = sensor_data['current'].get('timestamp')


# ─── Rutas ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html', data=sensor_data)


@app.route('/data', methods=['POST'])
def receive_data():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Request must be JSON'}), 400


    try:
        data = request.get_json()
        print("DATO RECIBIDO:", data)
        # Validar campos mínimos requeridos
        required_fields = ['pm1_0', 'pm2_5', 'temperature', 'humidity']
        for field in required_fields:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400

        # Usar timestamp del ESP si está disponible
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # ── Guardar en MongoDB Atlas ──
        result = collection.insert_one(data)
        print("GUARDADO EN MONGO, id:", result.inserted_id)

        # ── Actualizar caché en memoria ──
        sensor_data['current'] = data
        sensor_data['last_update'] = data['timestamp']
        sensor_data['history'].append(data)
        if len(sensor_data['history']) > 100:
            sensor_data['history'] = sensor_data['history'][-100:]

        return jsonify({'status': 'success'})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/mapa')
def mostrar_mapa():
    pm25 = sensor_data['current'].get('pm2_5', 0) if sensor_data['current'] else 0
    lat, lon = 3.452065680855233, -76.53538487798981

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
    ultimos = sensor_data['history'][-20:]
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
    try:
        history = list(collection.find({}, {'_id': 0}).sort('timestamp', 1).limit(100))
    except:
        history = sensor_data['history'][-20:]
    return render_template('dashboard.html', history=history)


@app.route('/api/data')
def get_data():
    return jsonify(sensor_data)


@app.route('/api/historial')
def get_historial():
    """Devuelve todos los registros guardados en MongoDB."""
    try:
        registros = list(collection.find({}, {'_id': 0}).sort('timestamp', -1).limit(500))
        return jsonify({'status': 'success', 'total': len(registros), 'data': registros})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)




