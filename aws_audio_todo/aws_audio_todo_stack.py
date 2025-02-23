from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_lambda_event_sources as lambda_events,
    aws_iam as iam,
    Duration, CfnParameter
)
from constructs import Construct


class AwsAudioTodoStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        things3_email_param = CfnParameter(self, "Things3Email")
        sender_email_param = CfnParameter(self, "SenderEmail")

        # Create an Amazon S3 bucket to store audio files uploaded from users
        audio_bucket = s3.Bucket(self, "AudioBucket")

        # Define the AWS Lambda function responsible for receiving and uploading audio files
        audio_upload_lambda = _lambda.Function(
            self,
            "AudioUploadLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,  # Using Python 3.12 runtime for the Lambda function
            handler="lambda_function.lambda_handler",  # Entry point function for Lambda (lambda_function.py)
            code=_lambda.Code.from_asset("aws_audio_todo/lambda/audio_upload"),  # Path to your Lambda code
            environment={
                # Pass the S3 bucket name as an environment variable to Lambda
                "BUCKET_NAME": audio_bucket.bucket_name
            },
            tracing = _lambda.Tracing.ACTIVE,
        )

        # Grant the Lambda function permissions to put (upload) objects into the S3 bucket
        audio_bucket.grant_put(audio_upload_lambda)

        # Create an API Gateway REST API to trigger the Lambda function via HTTP requests
        api = apigw.LambdaRestApi(
            self,
            "AudioUploadApi",
            handler=audio_upload_lambda,
            proxy=False  # Disable automatic proxy integration to define routes explicitly
        )

        # Explicitly define a POST method at the '/upload' endpoint on the API Gateway
        upload_resource = api.root.add_resource("upload")
        upload_resource.add_method("POST") # Connect POST requests on '/upload' to the Lambda function

        transcription_lambda = _lambda.Function(
            self, "TranscriptionLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="transcription_handler.lambda_handler",
            code=_lambda.Code.from_asset("aws_audio_todo/lambda/transcription"),
            environment={
                "BUCKET_NAME": audio_bucket.bucket_name,
                "TRANSCRIPTS_FOLDER": "transcripts/"
            },
            timeout=Duration.minutes(5),
            tracing=_lambda.Tracing.ACTIVE,
        )

        # Trigger Transcription Lambda automatically upon audio file upload
        transcription_lambda.add_event_source(
            lambda_events.S3EventSource(
                audio_bucket,
                events=[s3.EventType.OBJECT_CREATED],
                filters=[s3.NotificationKeyFilter(prefix="audio/")]
            )
        )

        # Permissions to access Transcribe and S3
        transcription_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["transcribe:*"],
            resources=["*"]
        ))
        audio_bucket.grant_read_write(transcription_lambda)

        # === NEW: Task Generator Lambda (Bedrock/OpenAI) ===
        task_generator_lambda = _lambda.Function(
            self, "TaskGeneratorLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="task_generator.lambda_handler",
            code=_lambda.Code.from_asset("aws_audio_todo/lambda/task_generator"),
            environment={
                "BUCKET_NAME": audio_bucket.bucket_name,
                "TRANSCRIPTS_FOLDER": "transcripts/",
                "TASKS_FOLDER": "tasks/"
            },
            timeout=Duration.minutes(5),
            tracing=_lambda.Tracing.ACTIVE,
        )

        # Trigger Lambda on transcript file creation
        task_generator_lambda.add_event_source(
            lambda_events.S3EventSource(
                audio_bucket,
                events=[s3.EventType.OBJECT_CREATED],
                filters=[s3.NotificationKeyFilter(prefix="transcripts/")]
            )
        )

        # Permissions
        audio_bucket.grant_read_write(task_generator_lambda)

        # Bedrock permissions (if using AWS Bedrock)
        task_generator_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:*", "bedrock-runtime:*"],
            resources=["*"]
        ))

        ses_lambda = _lambda.Function(
            self, "SesEmailSenderLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="ses_email_sender.lambda_handler",
            code=_lambda.Code.from_asset("aws_audio_todo/lambda/ses_email_sender"),
            environment={
                "BUCKET_NAME": audio_bucket.bucket_name,
                "THINGS3_EMAIL": things3_email_param.value_as_string,
                "SENDER_EMAIL": sender_email_param.value_as_string
            },
            timeout=Duration.minutes(2),
            tracing=_lambda.Tracing.ACTIVE,
        )

        # Trigger Lambda when a new task file is created
        ses_lambda.add_event_source(
            lambda_events.S3EventSource(
                audio_bucket,
                events=[s3.EventType.OBJECT_CREATED],
                filters=[s3.NotificationKeyFilter(prefix="tasks/", suffix="-tasks.txt")]
            )
        )

        # Permissions for SES Lambda
        audio_bucket.grant_read(ses_lambda)
        ses_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["ses:SendEmail"],
            resources=["*"]
        ))



