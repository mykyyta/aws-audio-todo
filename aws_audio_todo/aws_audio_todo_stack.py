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

        audio_bucket = s3.Bucket(self, "AudioBucket")

        audio_upload_lambda = _lambda.Function(
            self,
            "AudioUploadLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("aws_audio_todo/lambda/audio_upload"),
            environment={
                "BUCKET_NAME": audio_bucket.bucket_name
            },
            tracing = _lambda.Tracing.ACTIVE,
        )

        audio_bucket.grant_put(audio_upload_lambda)

        api = apigw.LambdaRestApi(
            self,
            "AudioUploadApi",
            handler=audio_upload_lambda,
            proxy=False  # Disable automatic proxy integration to define routes explicitly
        )

        upload_resource = api.root.add_resource("upload")
        upload_resource.add_method("POST")

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

        transcription_lambda.add_event_source(
            lambda_events.S3EventSource(
                audio_bucket,
                events=[s3.EventType.OBJECT_CREATED],
                filters=[s3.NotificationKeyFilter(prefix="audio/")]
            )
        )


        transcription_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["transcribe:*"],
            resources=["*"]
        ))
        audio_bucket.grant_read_write(transcription_lambda)


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


        task_generator_lambda.add_event_source(
            lambda_events.S3EventSource(
                audio_bucket,
                events=[s3.EventType.OBJECT_CREATED],
                filters=[s3.NotificationKeyFilter(prefix="transcripts/")]
            )
        )

        audio_bucket.grant_read_write(task_generator_lambda)

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

        ses_lambda.add_event_source(
            lambda_events.S3EventSource(
                audio_bucket,
                events=[s3.EventType.OBJECT_CREATED],
                filters=[s3.NotificationKeyFilter(prefix="tasks/", suffix="-tasks.txt")]
            )
        )

        audio_bucket.grant_read(ses_lambda)
        ses_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["ses:SendEmail"],
            resources=["*"]
        ))



