import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de la App
app = Flask(__name__)
CORS(app)  # Permite que tu frontend se comunique con este backend

# Conexión a Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# --- RUTAS DE LA API ---

# Ruta de prueba
@app.route('/')
def home():
    return "¡El Backend de TodoStock SPA está funcionando!"

# --- GESTIÓN DE CLIENTES ---
@app.route('/api/clientes', methods=['GET'])
def get_clientes():
    """Obtiene todos los clientes."""
    try:
        response = supabase.table('clientes').select("*").order('nombre').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/clientes', methods=['POST'])
def create_cliente():
    """Crea un nuevo cliente."""
    try:
        data = request.get_json()
        if not data.get('nombre') or not data.get('rut'):
            return jsonify({"error": "Nombre y RUT son requeridos"}), 400
        response = supabase.table('clientes').insert(data).execute()
        return jsonify(response.data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GESTIÓN DE PRODUCTOS (INVENTARIO) ---
@app.route('/api/productos', methods=['GET'])
def get_productos():
    """Obtiene todos los productos del inventario."""
    try:
        response = supabase.table('productos').select("*").order('nombre_producto').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/productos', methods=['POST'])
def create_producto():
    """Añade un nuevo producto al inventario."""
    try:
        data = request.get_json()
        if not all(k in data for k in ['codigo_producto', 'nombre_producto', 'stock']):
            return jsonify({"error": "Código, nombre y stock son requeridos"}), 400
        response = supabase.table('productos').insert(data).execute()
        return jsonify(response.data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/productos/<int:id>', methods=['PUT'])
def update_producto(id):
    """Actualiza un producto existente (ej: ajustar stock)."""
    try:
        data = request.get_json()
        response = supabase.table('productos').update(data).eq('id', id).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- GESTIÓN DE VENTAS ---
@app.route('/api/ventas', methods=['POST'])
def create_venta():
    """Crea una nueva venta y descuenta el stock."""
    try:
        data = request.get_json()
        
        # Validación de datos básicos de la venta
        if not all(k in data for k in ['cliente_id', 'es_afecta_iva', 'detalles']):
            return jsonify({"error": "Faltan datos de la venta"}), 400
        if not data['detalles']:
            return jsonify({"error": "La venta debe tener al menos un producto"}), 400

        # 1. Descontar el stock de cada producto
        for item in data['detalles']:
            # Obtenemos el stock actual del producto
            producto_actual = supabase.table('productos').select('stock').eq('id', item['producto_id']).single().execute().data
            if not producto_actual:
                return jsonify({"error": f"Producto con id {item['producto_id']} no encontrado"}), 404
            
            stock_actual = producto_actual['stock']
            
            if stock_actual < item['cantidad']:
                return jsonify({"error": f"Stock insuficiente para el producto con id {item['producto_id']}"}), 400
            
            # Calculamos el nuevo stock y lo actualizamos
            nuevo_stock = stock_actual - item['cantidad']
            supabase.table('productos').update({'stock': nuevo_stock}).eq('id', item['producto_id']).execute()

        # 2. Calcular el total de la venta
        total_venta = sum(item['cantidad'] * item['precio_unitario'] for item in data['detalles'])

        # 3. Crear el registro de la venta
        venta_data = {
            'cliente_id': data['cliente_id'],
            'es_afecta_iva': data['es_afecta_iva'],
            'cantidad_bultos': data.get('cantidad_bultos', 1), # Si no se especifica, es 1 bulto
            'total': total_venta
        }
        venta_creada = supabase.table('ventas').insert(venta_data).execute().data[0]
        
        # 4. Crear los detalles de la venta
        detalles_data = []
        for item in data['detalles']:
            detalles_data.append({
                'venta_id': venta_creada['id'],
                'producto_id': item['producto_id'],
                'cantidad': item['cantidad'],
                'precio_unitario': item['precio_unitario']
            })
        supabase.table('detalles_venta').insert(detalles_data).execute()

        return jsonify({"message": "Venta creada exitosamente", "venta": venta_creada}), 201

    except Exception as e:
        # Aquí se debería implementar una lógica para revertir el stock si algo falla
        return jsonify({"error": str(e)}), 500
@app.route('/api/ventas/<int:id>', methods=['DELETE'])
def delete_venta(id):
    """Elimina una venta y sus detalles. No revierte el stock."""
    try:
        # La base de datos está configurada para borrar en cascada,
        # así que al borrar una venta, sus detalles se borran automáticamente.
        response = supabase.table('ventas').delete().eq('id', id).execute()
        
        if not response.data:
            return jsonify({"error": "Venta no encontrada"}), 404
            
        return jsonify({"message": "Venta eliminada exitosamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ventas', methods=['GET'])
def get_ventas():
    """Obtiene un listado de todas las ventas con todos los datos del cliente."""
    try:
        # Esta consulta une la tabla de ventas con la de clientes para obtener todos los datos (*)
        response = supabase.table('ventas').select('*, clientes(*)').order('fecha', desc=True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ANÁLISIS ---
@app.route('/api/analisis/ventas_mensuales', methods=['GET'])
def get_ventas_mensuales():
    """Genera un análisis de ventas totales por mes."""
    try:
        response = supabase.table('ventas').select('fecha, total').execute().data
        
        ventas_por_mes = {}
        for venta in response:
            fecha = datetime.fromisoformat(venta['fecha'])
            mes_anio = fecha.strftime('%Y-%m') # Formato "Año-Mes"
            
            if mes_anio not in ventas_por_mes:
                ventas_por_mes[mes_anio] = 0
            ventas_por_mes[mes_anio] += float(venta['total'])
            
        # Ordenar por fecha
        ventas_ordenadas = sorted(ventas_por_mes.items())
        
        return jsonify(ventas_ordenadas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/analisis/libro_ventas', methods=['GET'])
def get_libro_ventas():
    """Prepara los datos para un informe de ventas detallado."""
    try:
        # Consulta mejorada que obtiene todas las ventas y sus detalles
        response = supabase.table('ventas').select(
            '*, detalles_venta(*, productos(*))'
        ).order('fecha', desc=True).execute()
        
        # Procesar para mantener solo items con detalles
        processed_data = []
        for venta in response.data:
            if venta['detalles_venta']:
                for detalle in venta['detalles_venta']:
                    # Aplanar la estructura para el frontend
                    processed_data.append({
                        'cantidad': detalle['cantidad'],
                        'precio_unitario': detalle['precio_unitario'],
                        'ventas': {
                            'fecha': venta['fecha'],
                            'es_afecta_iva': venta['es_afecta_iva']
                        },
                        'productos': detalle['productos']
                    })

        return jsonify(processed_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500