from fastapi import FastAPI, HTTPException
import os
from mangum import Mangum
from models import QueryRequest, QueryResult
from myrag import query_rag
import boto3, json

# Initialize FastAPI app
app = FastAPI()

# In-memory storage for queries and results
IS_WORKER_LAMBDA_AVAILABLE = os.environ.get("IS_WORKER_LAMBDA_AVAILABLE", None)


@app.get("/")
def index():
    return {"message": "Welcome to the Query Processing API!"}




def invoke_worker_lambda_func(query: QueryResult):
    # Initialize the Lambda client
    lambda_client = boto3.client("lambda")

    # Get the QueryResult as a dictionary.
    print(type(query))
    payload = query.to_dict()

    # Invoke another Lambda function asynchronously
    response = lambda_client.invoke(
        FunctionName=IS_WORKER_LAMBDA_AVAILABLE,
        InvocationType="Event",
        Payload=json.dumps(payload),
    )

    print(f"✅ Worker Lambda invoked: {response}")



# Endpoint to submit a query
@app.post("/submit_query", response_model=QueryResult)
async def submit_query(request: QueryRequest):
    query_text = request.query_text

    qr = QueryResult(query_text=query_text)



    if IS_WORKER_LAMBDA_AVAILABLE:
        qr.put_item_into_table()
        invoke_worker_lambda_func(qr)
    
    else:

        # Process the query, wait for the result
        answer = query_rag(query_text)

        qr.answer_text = answer.get("answer")
        qr.sources = [x.page_content for x in answer.get("context") if x.page_content]
        qr.is_complete = True

        qr.put_item_into_table()
    return qr



# Endpoint to retrieve query results
@app.get("/get_query/{query_id}", response_model=QueryResult)
async def get_query(query_id: str):
    query = QueryResult.get_item_from_table(query_id)
    return query

# Placeholder function to process the query
def process_query(query):
    # Implement your query processing logic here
    return f"Processed result for query: {query}"

# Use Mangum to make the FastAPI app compatible with AWS Lambda
handler = Mangum(app)

# Run the FastAPI app with Uvicorn (for local testing)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)