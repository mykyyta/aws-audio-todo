import boto3
import uuid
import os

transcribe = boto3.client('transcribe')

BUCKET_NAME = os.environ['BUCKET_NAME']
TRANSCRIPTS_FOLDER = os.environ['TRANSCRIPTS_FOLDER']

def lambda_handler(event, context):
    for record in event['Records']:
        audio_key = record['s3']['object']['key']
        job_name = f"transcribe-{uuid.uuid4()}"

        audio_uri = f"s3://{BUCKET_NAME}/{audio_key}"

        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            IdentifyLanguage=True,
            LanguageOptions=['en-US', 'uk-UA', 'ru-RU'],
            MediaFormat='m4a',
            Media={'MediaFileUri': audio_uri},
            OutputBucketName=BUCKET_NAME,
            OutputKey=f"{TRANSCRIPTS_FOLDER}{job_name}.json"
        )

        print(f"✅ Started transcription: {job_name} for {audio_key}")

    return {"status": "Transcribe jobs started"}