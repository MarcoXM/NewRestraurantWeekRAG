# Query Processing API

This project is a Query Processing API built with FastAPI and AWS Lambda. It allows users to process queries and store results using an in-memory storage system. The project leverages AWS services such as Lambda and DynamoDB for scalable and serverless query processing.

## Features

- **FastAPI**: A modern, fast (high-performance), web framework for building APIs with Python 3.6+ based on standard Python type hints.
- **AWS Lambda**: Serverless compute service that runs code in response to events and automatically manages the underlying compute resources.
- **DynamoDB**: A fully managed NoSQL database service that provides fast and predictable performance with seamless scalability.
- **Mangum**: An adapter for using ASGI applications with AWS Lambda & API Gateway.

## Project Structure
/Users/marcowang/projects/crawler 
├── app 
│ ├── api.py 
│ ├── models.py 
│ └── myrag.py 
├── Dockerfile 
├── requirements.txt 
├── .env 
├── rag-app-cdk-python 
│ ├── rag-app-cdk-python 
│ ├──stack.py 
└── ...

## Setup

### Prerequisites

- Python 3.11
- Docker
- AWS CLI
- AWS CDK

### Installation

1. **Clone the repository**:
```sh
git clone https://github.com/MarcoXM/NewRestraurantWeekRAG.git
cd your-repo
```

2. **Create and activate a virtual environment**:
```sh
python -m venv .venv
source .venv/bin/activate  
```

3. **Install dependencies** :
```sh
pip install -r requirements.txt
```

4. **Set up AWS credentials**:
```sh
aws configure
```

5. **Bootstrap the CDK environment**:
```sh
cdk bootstrap aws://<account-id>/<region>

```
## Environment Variables
Create a .env file in the root directory and add the following environment variables:
```sh

AWS_ACCOUNT_ID=<your-aws-account-id>
AWS_REGION=<your-aws-region>
OPENAI_API_KEY=<your-openai-api-key>
IS_WORKER_LAMBDA_AVAILABLE=<your-worker-lambda-function-name>
```
## Build and Deploy
1. **Build the Docker image:**
```sh
docker build --platform linux/amd64 -t app .

```
2. **Deploy the CDK stack:**
```sh
cdk deploy

```

## Usage
### Running Locally
1. Run the Docker container:
```sh
docker run -p 8000:8000 app
```
2. Access the API: Open your web browser and navigate to http://localhost:8000 to access the Query Processing API.

API Endpoints
GET /: Welcome message
POST /submit_query: Submit a query and get results
Example Code


## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details. `