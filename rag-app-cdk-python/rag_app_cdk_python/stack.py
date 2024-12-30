from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_logs as logs,
    CfnOutput,
    aws_ssm as ssm,
    App,
    Tags,
)
from constructs import Construct
from dotenv import load_dotenv
import os
from pathlib import Path

class RagAppCdkPythonStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
       # Debug: Print the path we're looking for .env
        dotenv_path = Path(__file__).parent.parent / '.env'
        print(f"Looking for .env file at: {dotenv_path.absolute()}")
        
        # Debug: Verify .env file exists
        if not dotenv_path.exists():
            print(dotenv_path.absolute())
            raise FileNotFoundError(f".env file not found at {dotenv_path.absolute()}")
        
        load_dotenv(dotenv_path=dotenv_path.absolute())
        print("Loaded .env file")


        # Create secure parameters in Parameter Store
        openai_key_param = ssm.StringParameter(
            self, "OpenAIKey",
            parameter_name="/rag-app/openai-api-key",
            string_value=os.getenv("OPENAI_API_KEY", ""),
            tier=ssm.ParameterTier.ADVANCED  # Encrypts the value
        )


        # Create a DynamoDB table to store the query data and results.
        rag_query_table = dynamodb.Table(
            self, "RagQueryTable",
            partition_key=dynamodb.Attribute(name="query_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        # Function to handle the API requests. Uses same base image, but different handler.

        api_image_code = _lambda.DockerImageCode.from_image_asset(
            "../",  # Better directory structure
            cmd=["app.api.handler"], # Handler for the API function Mangum
            exclude=[
                'cdk.out',
                '.git',
                'node_modules',
                '*.pyc',
                '__pycache__',
                '.env'
            ],
            build_args={
                "platform": "linux/amd64"
            }
        )
        api_function = _lambda.DockerImageFunction(
            self, "ApiFunc",
            code=api_image_code,
            memory_size=256,
            timeout=Duration.seconds(30),
            architecture=_lambda.Architecture.X86_64,
            environment={
                "TABLE_NAME": rag_query_table.table_name,
                "LOG_LEVEL": "INFO",
                "POWERTOOLS_SERVICE_NAME": "rag-api",
                "POWERTOOLS_METRICS_NAMESPACE": "RagApp",
                "PYTHONPATH": "/var/task:/var/task/app",

                "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
                "REGION": os.getenv("REGION", "us-east-1"),
                
                # References to secure parameters
                "OPENAI_API_KEY": openai_key_param.string_value,
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
            tracing=_lambda.Tracing.ACTIVE  # Enable X-Ray tracing
        )


        # Grant the Lambda function permission to read the parameters
        openai_key_param.grant_read(api_function)

        # Grant the Lambda function permission to write to the DynamoDB table
        rag_query_table.grant_write_data(api_function)
        rag_query_table.grant_read_data(api_function)


        # Public URL for the API function.
        # Configure function URL with CORS
        function_url = api_function.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,
            cors={
                'allowed_origins': ['*'],  # Restrict this in production
                'allowed_methods': [_lambda.HttpMethod.ALL],
                'allowed_headers': ['*']
            }
        )
        # Output the URL for the API function.
        # Add outputs for important resources
        CfnOutput(self, "FunctionUrl", 
                 value=function_url.url,
                 description="API endpoint URL")
        
