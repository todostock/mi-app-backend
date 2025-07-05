import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de la App
app = Flask(__name__)
CORS(app) # Permite que tu frontend se comunique con este backend

# Conexión a Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# --- RUTAS DE LA API ---

# Ruta de prueba
@app.route('/')
def home():
    return "¡El Backend está funcionando!"

# --- CLIENTES ---
@app.route('/api/clientes', methods=['GET'])
def get_clientes():
    response = supabase.table('Clientes').select("*").order('nombre').execute()
    return jsonify(response.data)

@app.route('/api/clientes', methods=['POST'])
def create_cliente():
    data = request.get_json()
    # Aquí iría la validación de datos
    response = supabase.table('Clientes').insert(data).execute()
    return jsonify(response.data)

# --- PRODUCTOS ---
@app.route('/api/productos', methods=['GET'])
def get_productos():
    response = supabase.table('Productos').select("*").order('nombre_producto').execute()
    return jsonify(response.data)

# ... Aquí crearías las rutas para POST (crear), PUT (actualizar), DELETE (borrar) para cada tabla ...
# La ruta para crear una VENTA sería la más compleja, porque debe actualizar el stock.

if __name__ == '__main__':
    app.run(debug=True)