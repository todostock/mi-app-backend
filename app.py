import os
from flask import Flask, request, jsonify
from flask_cors import CORS # Asegúrate que esta línea esté
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps

load_dotenv()
app = Flask(__name__)

# --- CONFIGURACIÓN DE CORS EXPLÍCITA PARA PRODUCCIÓN ---
# Esto le dice a nuestro backend que acepte peticiones desde cualquier origen ('*')
# para todas las rutas que empiecen con /api/
CORS(app, resources={r"/api/*": {"origins": "*"}})

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

# --- TODAS TUS OTRAS RUTAS VAN AQUÍ, SIN CAMBIOS ---
# (get_clientes, create_cliente, get_productos, etc.)

@app.route('/api/clientes', methods=['GET'])
@token_required
def get_clientes(user):
    try:
        response = supabase.table('clientes').select("*").order('nombre').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ... Pega aquí el resto de tus funciones de la API ...
# (create_cliente, get_productos, create_producto, update_producto, etc.
#  Asegúrate que todas las que deban estar protegidas tengan @token_required
#  y el parámetro 'user' en su definición, como ya lo habíamos hecho).


if __name__ == '__main__':
    app.run(debug=True)