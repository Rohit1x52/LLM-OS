from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from main import NLKernel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

kernel = NLKernel()

class QueryRequest(BaseModel):
    text: str

@app.post("/api/process")
async def process_query(request: QueryRequest):
    result = kernel.process(request.text)
    return result

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}