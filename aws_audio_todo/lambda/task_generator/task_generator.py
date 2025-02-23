import boto3
import json
import os

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime')

BUCKET_NAME = os.environ['BUCKET_NAME']
TRANSCRIPTS_FOLDER = os.environ['TRANSCRIPTS_FOLDER']
TASKS_FOLDER = os.environ['TASKS_FOLDER']

def lambda_handler(event, context):
    for record in event['Records']:
        transcript_key = record['s3']['object']['key']

        # Skip temporary files explicitly
        if transcript_key.startswith(TRANSCRIPTS_FOLDER + '.'):
            print(f"⚠️ Skipping temporary file: {transcript_key}")
            continue

        response = s3.get_object(Bucket=BUCKET_NAME, Key=transcript_key)
        transcript_json = json.loads(response['Body'].read())

        if not transcript_json:
            print(f"⚠️ Empty transcript JSON detected for {transcript_key}, skipping.")
            continue

        transcript_text = transcript_json['results']['transcripts'][0]['transcript']

        prompt = f"""
        Given the following transcript, extract clear actionable tasks in a simple list format:

        Transcript:
        {transcript_text}

        Tasks:
        """

        bedrock_response = bedrock.invoke_model(
            modelId="amazon.titan-text-express-v1",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 400,
                    "temperature": 0.0,
                    "topP": 1.0
                }
            })
        )

        result = json.loads(bedrock_response['body'].read())
        tasks_text = result['results'][0]['outputText']

        tasks_key = transcript_key.replace(TRANSCRIPTS_FOLDER, TASKS_FOLDER).replace('.json', '-tasks.txt')
        s3.put_object(Bucket=BUCKET_NAME, Key=tasks_key, Body=tasks_text.encode('utf-8'))

        print(f"✅ Tasks generated and saved: {tasks_key}")

    return {"status": "tasks generated"}