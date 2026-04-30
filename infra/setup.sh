# crea RDS, SQS, S3, SNS, Secrets Manager
#!/bin/bash
set -e
export AWS_PAGER=cat
REGION=us-east-1
EXPEDIENTE=753353
BUCKET="${EXPEDIENTE}-esi3898k-examen2"
DB_PASS="Password123!"
SNS_EMAIL="malop1237@gmail.com"

echo "=== 1. S3 ==="
aws s3 mb s3://$BUCKET --region $REGION
echo "Bucket: $BUCKET"

echo "=== 2. SNS ==="
SNS_ARN=$(aws sns create-topic --name notas-venta-topic-ex2 --region $REGION --query TopicArn --output text)
echo "SNS ARN: $SNS_ARN"
aws sns subscribe \
  --topic-arn $SNS_ARN \
  --protocol email \
  --notification-endpoint $SNS_EMAIL \
  --region $REGION
echo "Confirma la suscripcion en tu correo antes de continuar"

echo "=== 3. SQS ==="
SQS_URL=$(aws sqs create-queue \
  --queue-name notas-venta-queue \
  --region $REGION \
  --query QueueUrl --output text)
SQS_ARN=$(aws sqs get-queue-attributes \
  --queue-url $SQS_URL \
  --attribute-names QueueArn \
  --query Attributes.QueueArn --output text)
echo "SQS URL: $SQS_URL"
echo "SQS ARN: $SQS_ARN"

echo "=== 4. RDS Security Group ==="
VPCID=$(aws ec2 describe-vpcs \
  --filters Name=isDefault,Values=true \
  --query "Vpcs[0].VpcId" --output text --region $REGION)

SGRDS=$(aws ec2 create-security-group \
  --group-name examen2-rds-sg \
  --description "SG RDS examen2" \
  --vpc-id $VPCID \
  --region $REGION \
  --query GroupId --output text)

# Abre 5432 desde cualquier lugar dentro de la VPC
aws ec2 authorize-security-group-ingress \
  --group-id $SGRDS \
  --protocol tcp \
  --port 5432 \
  --cidr 0.0.0.0/0 \
  --region $REGION

echo "SG RDS: $SGRDS"

echo "=== 5. RDS ==="
aws rds create-db-instance \
  --db-instance-identifier examen2-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --allocated-storage 20 \
  --master-username postgres \
  --master-user-password $DB_PASS \
  --db-name ventas \
  --publicly-accessible \
  --vpc-security-group-ids $SGRDS \
  --backup-retention-period 0 \
  --region $REGION

echo "RDS creandose, espera 5-10 min..."
aws rds wait db-instance-available --db-instance-identifier examen2-db --region $REGION

DB_HOST=$(aws rds describe-db-instances \
  --db-instance-identifier examen2-db \
  --query "DBInstances[0].Endpoint.Address" \
  --output text --region $REGION)
echo "RDS Host: $DB_HOST"

echo "=== 6. Secrets Manager ==="
aws secretsmanager create-secret \
  --name examen2/db_host --secret-string "$DB_HOST" --region $REGION
aws secretsmanager create-secret \
  --name examen2/db_password --secret-string "$DB_PASS" --region $REGION
aws secretsmanager create-secret \
  --name examen2/sqs_url --secret-string "$SQS_URL" --region $REGION
aws secretsmanager create-secret \
  --name examen2/sns_arn --secret-string "$SNS_ARN" --region $REGION
aws secretsmanager create-secret \
  --name examen2/s3_bucket --secret-string "$BUCKET" --region $REGION

echo ""
echo "=== LISTO ==="
echo "DB_HOST=$DB_HOST"
echo "SQS_URL=$SQS_URL"
echo "SNS_ARN=$SNS_ARN"
echo "BUCKET=$BUCKET"
echo "SG_RDS=$SGRDS"