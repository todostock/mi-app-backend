import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps

load_dotenv()
app = Flask(__name__)

# --- CONFIGURACIÓN DE CORS EXPLÍCITA Y FINAL PARA PRODUCCIÓN ---
# Esto resuelve el error de "preflight" al permitir explícitamente los métodos
# y cabeceras que usamos en nuestra aplicación.
CORS(app, resources={r"/api/*": {
    "origins": "*",  # Permite cualquier origen (o puedes poner tu URL de Vercel para más seguridad)
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type"]
}})

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
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

@app.route('/')
def home():
    return "¡El Backend de TodoStock SPA está funcionando!"

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    try:
        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return jsonify({ "access_token": session.session.access_token, "user": session.user.email })
    except Exception as e:
        return jsonify({"message": "Credenciales inválidas"}), 401

# --- TODAS LAS RUTAS PROTEGIDAS ---
# (El resto del archivo se mantiene exactamente igual que la versión anterior)

@app.route('/api/clientes', methods=['GET'])
@token_required
def get_clientes(user):
    try:
        response = supabase.table('clientes').select("*").order('nombre').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/clientes', methods=['POST'])
@token_required
def create_cliente(user):
    # (El código de tu función va aquí)
    data = request.get_json()
    response = supabase.table('clientes').insert(data).execute()
    return jsonify(response.data), 201

@app.route('/api/productos', methods=['GET'])
@token_required
def get_productos(user):
    # (El código de tu función va aquí)
    response = supabase.table('productos').select("*").order('nombre_producto').execute()
    return jsonify(response.data)

# ... Y ASÍ CON EL RESTO DE TUS FUNCIONES ...
# (create_producto, update_producto, create_venta, get_ventas, delete_venta, get_libro_ventas)
# Cópialas de tu archivo actual y pégalas aquí.

if __name__ == '__main__':
    app.run(debug=True)