import aws_cdk as core
import aws_cdk.assertions as assertions

from rag_app_cdk_python.stack import RagAppCdkPythonStack

# example tests. To run these tests, uncomment this file along with the example
# resource in rag_app_cdk_python/rag_app_cdk_python_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = RagAppCdkPythonStack(app, "rag-app-cdk-python")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
