# Examen Practico 2 - API REST en Kubernetes
Manuel Lopez - Desarrollo en la Nube

## Que hace este proyecto

Es una API REST de ventas desplegada en un cluster de Kubernetes en AWS (EKS).
El sistema permite gestionar clientes, domicilios, productos y notas de venta.
Cuando se crea una nota, se genera un PDF, se sube a S3 y se le manda un correo
al cliente con el link de descarga. Todo corre en la nube, sin nada en localhost.

## Arquitectura

El sistema se divide en 4 pods que se comunican entre si:

- api: recibe todas las peticiones HTTP. Es el unico pod expuesto al exterior
  via un LoadBalancer. Cuando se crea una nota, publica un mensaje en SQS y
  responde inmediatamente sin esperar a que el PDF se genere.

- receipt-worker: escucha la cola de SQS constantemente. Cuando llega un mensaje,
  consulta RDS para obtener los datos de la nota y coordina el flujo: le pide al
  pdf-generator que genere el PDF y luego le pide al notifier que mande el correo.
  Este pod no tiene Service porque no recibe trafico, solo consume mensajes.

- pdf-generator: recibe los datos de una nota, genera el PDF con ReportLab,
  lo sube a S3 con 3 metadatos (hora-envio, nota-descargada, veces-enviado)
  y devuelve la URL de descarga.

- notifier: recibe el folio y el correo del cliente y manda la notificacion
  via AWS SNS.

Servicios de AWS utilizados: EKS, RDS (PostgreSQL), SQS, S3, SNS, Secrets Manager.

## Estructura del repositorio

SegundoExamenPractico/
├── infra/
│   ├── setup.sh          # crea RDS, SQS, S3, SNS y Secrets Manager
│   └── cluster.yaml      # definicion del cluster EKS
├── k8s/
│   ├── configmap.yaml
│   ├── api-deployment.yaml
│   ├── pdf-generator-deployment.yaml
│   ├── notifier-deployment.yaml
│   └── receipt-worker-deployment.yaml
├── services/
│   ├── api/
│   ├── pdf-generator/
│   ├── notifier/
│   └── receipt-worker/
└── README.md

## Como desplegarlo

1. Configurar credenciales de AWS:
   aws sts get-caller-identity

2. Correr el script de infraestructura:
   chmod +x infra/setup.sh
   ./infra/setup.sh

3. Crear las tablas en RDS:
   psql -h TU_DB_HOST -U postgres -d ventas
   (pegar el SQL de las 5 tablas)

4. Crear el cluster de EKS:
   eksctl create cluster -f infra/cluster.yaml
   (tarda 15-20 minutos)

5. Build y push de las imagenes a Docker Hub:
   docker build -t manuellpz17/examen2-api:latest services/api/
   docker push manuellpz17/examen2-api:latest
   (igual para los otros 3 servicios)

6. Desplegar en Kubernetes:
   kubectl apply -f k8s/

7. Obtener la IP del LoadBalancer:
   kubectl get service api-service

8. Verificar que todo corre:
   kubectl get pods

## Secretos

Todos los valores sensibles estan en AWS Secrets Manager y se obtienen
en tiempo de ejecucion. Las entradas son:
- examen2/db_host
- examen2/db_password
- examen2/sqs_url
- examen2/sns_arn
- examen2/s3_bucket

## Docker Hub

- manuellpz17/examen2-api
- manuellpz17/examen2-pdf-generator
- manuellpz17/examen2-notifier
- manuellpz17/examen2-receipt-worker