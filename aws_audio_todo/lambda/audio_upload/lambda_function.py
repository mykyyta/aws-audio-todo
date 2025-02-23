import boto3
import base64
import uuid
import os
import json

s3 = boto3.client('s3')
BUCKET_NAME = os.environ['BUCKET_NAME']


def lambda_handler(event, context):
    try:
        body_json = json.loads(event['body'])
        audio_base64 = body_json['body']

        # Log only metadata
        print(f"Received audio data size (base64): {len(audio_base64)} characters")

        audio_data = base64.b64decode(audio_base64)
        audio_key = f"audio/{uuid.uuid4()}.m4a"

        s3.put_object(Bucket=BUCKET_NAME, Key=audio_key, Body=audio_data)

        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Audio successfully uploaded',
                'audio_key': audio_key
            })
        }

    except Exception as e:
        print("Error:", str(e))
        response = {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

    return response