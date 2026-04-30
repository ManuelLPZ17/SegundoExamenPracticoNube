import boto3
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_secret(name):
    client = boto3.client("secretsmanager", region_name="us-east-1")
    return client.get_secret_value(SecretId=name)["SecretString"]

@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json()
    folio = data["folio"]
    correo = data["correo"]
    url_descarga = data["url_descarga"]

    sns_arn = get_secret("examen2/sns_arn")
    sns = boto3.client("sns", region_name="us-east-1")
    sns.publish(
        TopicArn=sns_arn,
        Subject=f"Nota de venta {folio}",
        Message=f"Se genero tu nota de venta {folio}.\n\nDescargala aqui: {url_descarga}"
    )
    return jsonify({"message": "Notificacion enviada"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082, debug=True)