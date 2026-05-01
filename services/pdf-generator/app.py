import boto3
import io
from flask import Flask, request, jsonify
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime, timezone

app = Flask(__name__)


def get_secret(name):
    client = boto3.client("secretsmanager", region_name="us-east-1")
    return client.get_secret_value(SecretId=name)["SecretString"]

def generar_pdf(cliente, folio, contenido):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "NOTA DE VENTA")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 90, "Datos del Cliente")
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 110, f"Razon Social: {cliente['razon_social']}")
    c.drawString(50, height - 125, f"Nombre Comercial: {cliente['nombre_comercial']}")
    c.drawString(50, height - 140, f"RFC: {cliente['rfc']}")
    c.drawString(50, height - 155, f"Correo: {cliente['correo']}")
    c.drawString(50, height - 170, f"Telefono: {cliente['telefono']}")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 200, f"Folio: {folio}")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, height - 230, "Cantidad")
    c.drawString(150, height - 230, "Producto")
    c.drawString(350, height - 230, "Precio Unitario")
    c.drawString(480, height - 230, "Importe")
    c.setFont("Helvetica", 11)
    y = height - 250
    for item in contenido:
        c.drawString(50, y, str(item["cantidad"]))
        c.drawString(150, y, item["nombre_producto"])
        c.drawString(350, y, f"${item['precio_unitario']:.2f}")
        c.drawString(480, y, f"${item['importe']:.2f}")
        y -= 20
    c.save()
    buffer.seek(0)
    return buffer

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    cliente = data["cliente"]
    folio = data["folio"]
    contenido = data["contenido"]

    bucket = get_secret("examen2/s3_bucket")
    s3_key = f"{cliente['rfc']}/{folio}.pdf"
    hora = datetime.now(timezone.utc).isoformat()

    pdf_buffer = generar_pdf(cliente, folio, contenido)

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=pdf_buffer,
        ContentType="application/pdf",
        Metadata={
            "hora-envio": hora,
            "nota-descargada": "false",
            "veces-enviado": "1"
        }
    )
    url = f"http://EXTERNAL-IP/notas/{folio}/download"
  #  url = f"http://API_SERVICE_URL:8080/notas/{folio}/download"
    return jsonify({"url": url, "s3_key": s3_key})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081, debug=True)