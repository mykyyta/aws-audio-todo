import boto3
import os

s3 = boto3.client('s3')
ses = boto3.client('ses')

BUCKET_NAME = os.environ['BUCKET_NAME']
THINGS3_EMAIL = os.environ['THINGS3_EMAIL']
SENDER_EMAIL = os.environ['SENDER_EMAIL']

def lambda_handler(event, context):
    for record in event['Records']:
        task_key = record['s3']['object']['key']

        response = s3.get_object(Bucket=BUCKET_NAME, Key=task_key)
        task_content = response['Body'].read().decode('utf-8')


        ses.send_email(
            Source=SENDER_EMAIL,
            Destination={"ToAddresses": [THINGS3_EMAIL]},
            Message={
                "Subject": {"Data": task_content},
                "Body": {"Text": {"Data": task_content}}
            }
        )

        print(f"✅ Email sent to Things 3: {task_key}")

    return {"status": "SES email sent"}