import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps

load_dotenv()
app = Flask(__name__)

# Configuración de CORS explícita para producción
CORS(app, resources={r"/api/*": {
    "origins": "*",
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type"]
}})

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# --- DECORADOR DE AUTENTICACIÓN CORREGIDO ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # --- LA CORRECCIÓN MÁS IMPORTANTE ESTÁ AQUÍ ---
        # Si la petición es de tipo OPTIONS (el "pre-vuelo" de CORS),
        # la aprobamos inmediatamente para que el navegador pueda enviar la petición real.
        if request.method == 'OPTIONS':
            return jsonify({'status': 'ok'}), 200

        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return jsonify({"message": "Falta el token de autenticación!"}), 401
        try:
            user = supabase.auth.get_user(token)
        except Exception as e:
            return jsonify({"message": "Token inválido o expirado!"}), 401
        
        return f(user, *args, **kwargs)
    return decorated

# --- RUTAS ---

@app.route('/')
def home():
    return "¡El Backend de TodoStock SPA está funcionando!"

@app.route('/api/login', methods=['POST'])
def login():
    # (El código de esta función se mantiene igual)
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    try:
        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return jsonify({ "access_token": session.session.access_token, "user": session.user.email })
    except Exception as e:
        return jsonify({"message": "Credenciales inválidas"}), 401

# --- TODAS TUS OTRAS RUTAS PROTEGIDAS VAN AQUÍ ---
# (Asegúrate de tener todas tus funciones como estaban antes)

@app.route('/api/clientes', methods=['GET'])
@token_required
def get_clientes(user):
    response = supabase.table('clientes').select("*").order('nombre').execute()
    return jsonify(response.data)

@app.route('/api/productos', methods=['GET'])
@token_required
def get_productos(user):
    response = supabase.table('productos').select("*").order('nombre_producto').execute()
    return jsonify(response.data)

@app.route('/api/analisis/libro_ventas', methods=['GET'])
@token_required
def get_libro_ventas(user):
    response = supabase.table('ventas').select('*, detalles_venta(*, productos(*))').order('fecha', desc=True).execute()
    processed_data = []
    for venta in response.data:
        if venta['detalles_venta']:
            for detalle in venta['detalles_venta']:
                processed_data.append({
                    'cantidad': detalle['cantidad'], 'precio_unitario': detalle['precio_unitario'],
                    'ventas': {'fecha': venta['fecha'], 'es_afecta_iva': venta['es_afecta_iva']},
                    'productos': detalle['productos']
                })
    return jsonify(processed_data)

# (Añade aquí el resto de tus rutas: POST, DELETE, etc., todas con @token_required y el parámetro 'user')
# ...

if __name__ == '__main__':
    app.run(debug=True)