from fastapi import FastAPI, HTTPException
import os
from mangum import Mangum
from models import QueryRequest, QueryResult
from myrag import query_rag
import uuid

# Initialize FastAPI app
app = FastAPI()

# In-memory storage for queries and results
id_2_queries = {}


@app.get("/")
def index():
    return {"message": "Welcome to the Query Processing API!"}


# Endpoint to submit a query
@app.post("/submit_query", response_model=QueryResult)
async def submit_query(request: QueryRequest):
    query_text = request.query_text

    query_response = query_rag(query_text)

    id_2_queries[query_response.query_id] = query_response
    return query_response



# Endpoint to retrieve query results
@app.get("/get_query/{query_id}", response_model=QueryResult)
async def get_query(query_id: str):
    if query_id not in id_2_queries:
        raise HTTPException(status_code=404, detail="Query not found")
    result = id_2_queries[query_id]
    return result

# Placeholder function to process the query
def process_query(query):
    # Implement your query processing logic here
    return f"Processed result for query: {query}"

# Use Mangum to make the FastAPI app compatible with AWS Lambda
handler = Mangum(app)

# Run the FastAPI app with Uvicorn (for local testing)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5050)