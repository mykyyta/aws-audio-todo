import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_audio_todo.aws_audio_todo_stack import AwsAudioTodoStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_audio_todo/aws_audio_todo_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsAudioTodoStack(app, "aws-audio-todo")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
