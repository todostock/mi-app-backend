import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps

# --- Cargar variables y configurar app ---
load_dotenv()
app = Flask(__name__)
CORS(app)
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# --- DECORADOR DE AUTENTICACIÓN ---
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

# --- RUTA PÚBLICA DE PRUEBA ---
@app.route('/')
def home():
    return "¡El Backend de TodoStock SPA está funcionando!"

# --- RUTA PÚBLICA DE LOGIN ---
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

# --- RUTAS PROTEGIDAS ---

# --- GESTIÓN DE CLIENTES ---
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
    try:
        data = request.get_json()
        response = supabase.table('clientes').insert(data).execute()
        return jsonify(response.data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GESTIÓN DE PRODUCTOS (INVENTARIO) ---
@app.route('/api/productos', methods=['GET'])
@token_required
def get_productos(user):
    try:
        response = supabase.table('productos').select("*").order('nombre_producto').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/productos', methods=['POST'])
@token_required
def create_producto(user):
    try:
        data = request.get_json()
        response = supabase.table('productos').insert(data).execute()
        return jsonify(response.data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/productos/<int:id>', methods=['PUT'])
@token_required
def update_producto(user, id):
    try:
        data = request.get_json()
        response = supabase.table('productos').update(data).eq('id', id).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GESTIÓN DE VENTAS ---
@app.route('/api/ventas', methods=['POST'])
@token_required
def create_venta(user):
    try:
        data = request.get_json()
        for item in data['detalles']:
            producto_actual = supabase.table('productos').select('stock').eq('id', item['producto_id']).single().execute().data
            stock_actual = producto_actual['stock']
            nuevo_stock = stock_actual - item['cantidad']
            supabase.table('productos').update({'stock': nuevo_stock}).eq('id', item['producto_id']).execute()
        total_venta = sum(item['cantidad'] * item['precio_unitario'] for item in data['detalles'])
        venta_data = {
            'cliente_id': data['cliente_id'], 'es_afecta_iva': data['es_afecta_iva'],
            'cantidad_bultos': data.get('cantidad_bultos', 1), 'total': total_venta
        }
        if data.get('fecha'):
            venta_data['fecha'] = data['fecha']
        venta_creada = supabase.table('ventas').insert(venta_data).execute().data[0]
        detalles_data = []
        for item in data['detalles']:
            detalles_data.append({
                'venta_id': venta_creada['id'], 'producto_id': item['producto_id'],
                'cantidad': item['cantidad'], 'precio_unitario': item['precio_unitario']
            })
        supabase.table('detalles_venta').insert(detalles_data).execute()
        return jsonify({"message": "Venta creada exitosamente", "venta": venta_creada}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ventas', methods=['GET'])
@token_required
def get_ventas(user):
    try:
        response = supabase.table('ventas').select('*, clientes(*)').order('fecha', desc=True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ventas/<int:id>', methods=['DELETE'])
@token_required
def delete_venta(user, id):
    try:
        response = supabase.table('ventas').delete().eq('id', id).execute()
        if not response.data:
            return jsonify({"error": "Venta no encontrada"}), 404
        return jsonify({"message": "Venta eliminada exitosamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ANÁLISIS ---
@app.route('/api/analisis/libro_ventas', methods=['GET'])
@token_required
def get_libro_ventas(user):
    try:
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)