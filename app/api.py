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

    qr = QueryResult(query_text=query_text)

    # Process the query
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