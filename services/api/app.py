import os
import json
import boto3
import psycopg2
from flask import Flask, request, jsonify, send_file
import io

app = Flask(__name__)

def get_secret(name):
    client = boto3.client("secretsmanager", region_name="us-east-1")
    return client.get_secret_value(SecretId=name)["SecretString"]

def get_connection():
    return psycopg2.connect(
        host=get_secret("examen2/db_host"),
        port=5432,
        database="ventas",
        user="postgres",
        password=get_secret("examen2/db_password")
    )

def get_sqs():
    return boto3.client("sqs", region_name="us-east-1")

# ==================== CLIENTES ====================

@app.route("/clientes/", methods=["POST"])
def crear_cliente():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Cuerpo vacio"}), 400
    for campo in ["razon_social", "nombre_comercial", "rfc", "correo", "telefono"]:
        if campo not in data or not str(data[campo]).strip():
            return jsonify({"error": f"Campo requerido: {campo}"}), 400
    if "@" not in data["correo"]:
        return jsonify({"error": "Correo invalido"}), 400
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clientes (razon_social, nombre_comercial, rfc, correo, telefono) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (data["razon_social"], data["nombre_comercial"], data["rfc"], data["correo"], data["telefono"])
    )
    id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Cliente creado", "id": id}), 201

@app.route("/clientes/", methods=["GET"])
def listar_clientes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, razon_social, nombre_comercial, rfc, correo, telefono FROM clientes")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([{"id":r[0],"razon_social":r[1],"nombre_comercial":r[2],"rfc":r[3],"correo":r[4],"telefono":r[5]} for r in rows])

@app.route("/clientes/<int:id>", methods=["GET"])
def obtener_cliente(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, razon_social, nombre_comercial, rfc, correo, telefono FROM clientes WHERE id=%s", (id,))
    r = cur.fetchone(); cur.close(); conn.close()
    if not r: return jsonify({"error": f"No existe cliente {id}"}), 404
    return jsonify({"id":r[0],"razon_social":r[1],"nombre_comercial":r[2],"rfc":r[3],"correo":r[4],"telefono":r[5]})

@app.route("/clientes/<int:id>", methods=["PUT"])
def actualizar_cliente(id):
    data = request.get_json()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM clientes WHERE id=%s", (id,))
    if not cur.fetchone(): cur.close(); conn.close(); return jsonify({"error": f"No existe cliente {id}"}), 404
    cur.execute(
        "UPDATE clientes SET razon_social=%s, nombre_comercial=%s, rfc=%s, correo=%s, telefono=%s WHERE id=%s",
        (data["razon_social"], data["nombre_comercial"], data["rfc"], data["correo"], data["telefono"], id)
    )
    conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Cliente actualizado"})

@app.route("/clientes/<int:id>", methods=["DELETE"])
def eliminar_cliente(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM clientes WHERE id=%s", (id,))
    if not cur.fetchone(): cur.close(); conn.close(); return jsonify({"error": f"No existe cliente {id}"}), 404
    cur.execute("DELETE FROM clientes WHERE id=%s", (id,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Cliente eliminado"})

# ==================== DOMICILIOS ====================

@app.route("/domicilios/", methods=["POST"])
def crear_domicilio():
    data = request.get_json()
    if not data: return jsonify({"error": "Cuerpo vacio"}), 400
    for campo in ["cliente_id", "domicilio", "colonia", "municipio", "estado", "tipo_direccion"]:
        if campo not in data: return jsonify({"error": f"Campo requerido: {campo}"}), 400
    if data["tipo_direccion"] not in ["FACTURACION", "ENVIO"]:
        return jsonify({"error": "tipo_direccion debe ser FACTURACION o ENVIO"}), 400
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM clientes WHERE id=%s", (data["cliente_id"],))
    if not cur.fetchone(): cur.close(); conn.close(); return jsonify({"error": f"No existe cliente {data['cliente_id']}"}), 404
    cur.execute(
        "INSERT INTO domicilios (cliente_id, domicilio, colonia, municipio, estado, tipo_direccion) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
        (data["cliente_id"], data["domicilio"], data["colonia"], data["municipio"], data["estado"], data["tipo_direccion"])
    )
    id = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Domicilio creado", "id": id}), 201

@app.route("/domicilios/", methods=["GET"])
def listar_domicilios():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, cliente_id, domicilio, colonia, municipio, estado, tipo_direccion FROM domicilios")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([{"id":r[0],"cliente_id":r[1],"domicilio":r[2],"colonia":r[3],"municipio":r[4],"estado":r[5],"tipo_direccion":r[6]} for r in rows])

@app.route("/domicilios/<int:id>", methods=["GET"])
def obtener_domicilio(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, cliente_id, domicilio, colonia, municipio, estado, tipo_direccion FROM domicilios WHERE id=%s", (id,))
    r = cur.fetchone(); cur.close(); conn.close()
    if not r: return jsonify({"error": f"No existe domicilio {id}"}), 404
    return jsonify({"id":r[0],"cliente_id":r[1],"domicilio":r[2],"colonia":r[3],"municipio":r[4],"estado":r[5],"tipo_direccion":r[6]})

@app.route("/domicilios/<int:id>", methods=["PUT"])
def actualizar_domicilio(id):
    data = request.get_json()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM domicilios WHERE id=%s", (id,))
    if not cur.fetchone(): cur.close(); conn.close(); return jsonify({"error": f"No existe domicilio {id}"}), 404
    cur.execute(
        "UPDATE domicilios SET cliente_id=%s, domicilio=%s, colonia=%s, municipio=%s, estado=%s, tipo_direccion=%s WHERE id=%s",
        (data["cliente_id"], data["domicilio"], data["colonia"], data["municipio"], data["estado"], data["tipo_direccion"], id)
    )
    conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Domicilio actualizado"})

@app.route("/domicilios/<int:id>", methods=["DELETE"])
def eliminar_domicilio(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM domicilios WHERE id=%s", (id,))
    if not cur.fetchone(): cur.close(); conn.close(); return jsonify({"error": f"No existe domicilio {id}"}), 404
    cur.execute("DELETE FROM domicilios WHERE id=%s", (id,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Domicilio eliminado"})

# ==================== PRODUCTOS ====================

@app.route("/productos/", methods=["POST"])
def crear_producto():
    data = request.get_json()
    if not data: return jsonify({"error": "Cuerpo vacio"}), 400
    for campo in ["nombre", "unidad_medida", "precio_base"]:
        if campo not in data: return jsonify({"error": f"Campo requerido: {campo}"}), 400
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO productos (nombre, unidad_medida, precio_base) VALUES (%s,%s,%s) RETURNING id",
        (data["nombre"], data["unidad_medida"], data["precio_base"])
    )
    id = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Producto creado", "id": id}), 201

@app.route("/productos/", methods=["GET"])
def listar_productos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, unidad_medida, precio_base FROM productos")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([{"id":r[0],"nombre":r[1],"unidad_medida":r[2],"precio_base":float(r[3])} for r in rows])

@app.route("/productos/<int:id>", methods=["GET"])
def obtener_producto(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, unidad_medida, precio_base FROM productos WHERE id=%s", (id,))
    r = cur.fetchone(); cur.close(); conn.close()
    if not r: return jsonify({"error": f"No existe producto {id}"}), 404
    return jsonify({"id":r[0],"nombre":r[1],"unidad_medida":r[2],"precio_base":float(r[3])})

@app.route("/productos/<int:id>", methods=["PUT"])
def actualizar_producto(id):
    data = request.get_json()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM productos WHERE id=%s", (id,))
    if not cur.fetchone(): cur.close(); conn.close(); return jsonify({"error": f"No existe producto {id}"}), 404
    cur.execute(
        "UPDATE productos SET nombre=%s, unidad_medida=%s, precio_base=%s WHERE id=%s",
        (data["nombre"], data["unidad_medida"], data["precio_base"], id)
    )
    conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Producto actualizado"})

@app.route("/productos/<int:id>", methods=["DELETE"])
def eliminar_producto(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM productos WHERE id=%s", (id,))
    if not cur.fetchone(): cur.close(); conn.close(); return jsonify({"error": f"No existe producto {id}"}), 404
    cur.execute("DELETE FROM productos WHERE id=%s", (id,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"message": "Producto eliminado"})

# ==================== NOTAS ====================

@app.route("/notas/", methods=["POST"])
def crear_nota():
    data = request.get_json()
    if not data: return jsonify({"error": "Cuerpo vacio"}), 400
    for campo in ["folio", "cliente_id", "direccion_facturacion", "direccion_envio", "total", "contenido"]:
        if campo not in data: return jsonify({"error": f"Campo requerido: {campo}"}), 400
    if not isinstance(data["contenido"], list) or len(data["contenido"]) == 0:
        return jsonify({"error": "contenido debe ser lista con al menos un item"}), 400

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM notas_venta WHERE folio=%s", (data["folio"],))
    if cur.fetchone(): cur.close(); conn.close(); return jsonify({"error": f"Folio ya existe: {data['folio']}"}), 400

    cur.execute("SELECT id FROM clientes WHERE id=%s", (data["cliente_id"],))
    if not cur.fetchone(): cur.close(); conn.close(); return jsonify({"error": f"No existe cliente {data['cliente_id']}"}), 404

    cur.execute(
        "INSERT INTO notas_venta (folio, cliente_id, direccion_facturacion, direccion_envio, total) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (data["folio"], data["cliente_id"], data["direccion_facturacion"], data["direccion_envio"], data["total"])
    )
    nota_id = cur.fetchone()[0]

    for item in data["contenido"]:
        cur.execute(
            "INSERT INTO contenido_nota (nota_id, producto_id, cantidad, precio_unitario, importe) VALUES (%s,%s,%s,%s,%s)",
            (nota_id, item["producto_id"], item["cantidad"], item["precio_unitario"], item["importe"])
        )
    conn.commit(); cur.close(); conn.close()

    # Publicar en SQS para que receipt-worker lo procese
    sqs = get_sqs()
    sqs_url = get_secret("examen2/sqs_url")
    sqs.send_message(
        QueueUrl=sqs_url,
        MessageBody=json.dumps({"nota_id": nota_id, "folio": data["folio"]})
    )

    return jsonify({"message": "Nota creada, procesando PDF en segundo plano", "id": nota_id, "folio": data["folio"]}), 201

@app.route("/notas/<folio>", methods=["GET"])
def leer_nota(folio):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT nv.id, nv.folio, nv.total,
               c.razon_social, c.nombre_comercial, c.rfc, c.correo, c.telefono
        FROM notas_venta nv
        JOIN clientes c ON c.id = nv.cliente_id
        WHERE nv.folio = %s
        """, (folio,)
    )
    r = cur.fetchone()
    if not r: cur.close(); conn.close(); return jsonify({"error": f"No existe nota {folio}"}), 404
    nota_id = r[0]
    cur.execute(
        """
        SELECT p.nombre, cn.cantidad, cn.precio_unitario, cn.importe
        FROM contenido_nota cn JOIN productos p ON p.id = cn.producto_id
        WHERE cn.nota_id = %s
        """, (nota_id,)
    )
    contenido = [{"nombre_producto":row[0],"cantidad":row[1],"precio_unitario":float(row[2]),"importe":float(row[3])} for row in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify({"folio":r[1],"total":float(r[2]),"cliente":{"razon_social":r[3],"nombre_comercial":r[4],"rfc":r[5],"correo":r[6],"telefono":r[7]},"contenido":contenido})

@app.route("/notas/<folio>/download", methods=["GET"])
def descargar_nota(folio):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT c.rfc FROM notas_venta nv JOIN clientes c ON c.id = nv.cliente_id WHERE nv.folio=%s",
        (folio,)
    )
    r = cur.fetchone(); cur.close(); conn.close()
    if not r: return jsonify({"error": f"No existe nota {folio}"}), 404

    rfc = r[0]
    bucket = get_secret("examen2/s3_bucket")
    s3_key = f"{rfc}/{folio}.pdf"
    s3 = boto3.client("s3", region_name="us-east-1")

    head = s3.head_object(Bucket=bucket, Key=s3_key)
    metadata = head["Metadata"]
    veces = int(metadata.get("veces-enviado", "1")) + 1
    from datetime import datetime, timezone
    hora = datetime.now(timezone.utc).isoformat()

    obj = s3.get_object(Bucket=bucket, Key=s3_key)
    pdf_data = obj["Body"].read()

    s3.copy_object(
        Bucket=bucket,
        CopySource={"Bucket": bucket, "Key": s3_key},
        Key=s3_key,
        Metadata={"hora-envio": hora, "nota-descargada": "true", "veces-enviado": str(veces)},
        MetadataDirective="REPLACE"
    )

    return send_file(io.BytesIO(pdf_data), mimetype="application/pdf", as_attachment=True, download_name=f"{folio}.pdf")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)