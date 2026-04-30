import boto3
import psycopg2
import json
import requests
import time

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

def procesar_mensaje(nota_id, folio):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT c.razon_social, c.nombre_comercial, c.rfc, c.correo, c.telefono
        FROM notas_venta nv JOIN clientes c ON c.id = nv.cliente_id
        WHERE nv.id = %s
        """, (nota_id,)
    )
    r = cur.fetchone()
    cliente = {"razon_social":r[0],"nombre_comercial":r[1],"rfc":r[2],"correo":r[3],"telefono":r[4]}

    cur.execute(
        """
        SELECT p.nombre, cn.cantidad, cn.precio_unitario, cn.importe
        FROM contenido_nota cn JOIN productos p ON p.id = cn.producto_id
        WHERE cn.nota_id = %s
        """, (nota_id,)
    )
    contenido = [{"nombre_producto":row[0],"cantidad":row[1],"precio_unitario":float(row[2]),"importe":float(row[3])} for row in cur.fetchall()]
    cur.close(); conn.close()

    # Solicitar PDF al pdf-generator
    pdf_resp = requests.post(
        "http://pdf-generator-service:8081/generate",
        json={"cliente": cliente, "folio": folio, "contenido": contenido}
    )
    url_descarga = pdf_resp.json()["url"]

    # Solicitar notificacion al notifier
    requests.post(
        "http://notifier-service:8082/notify",
        json={"folio": folio, "correo": cliente["correo"], "url_descarga": url_descarga}
    )

    print(f"Nota {folio} procesada correctamente")

def main():
    sqs = boto3.client("sqs", region_name="us-east-1")
    sqs_url = get_secret("examen2/sqs_url")
    print("receipt-worker iniciado, escuchando SQS...")

    while True:
        response = sqs.receive_message(
            QueueUrl=sqs_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10
        )
        messages = response.get("Messages", [])
        for msg in messages:
            body = json.loads(msg["Body"])
            try:
                procesar_mensaje(body["nota_id"], body["folio"])
                sqs.delete_message(QueueUrl=sqs_url, ReceiptHandle=msg["ReceiptHandle"])
            except Exception as e:
                print(f"Error procesando {body}: {e}")
        time.sleep(1)

if __name__ == "__main__":
    main()