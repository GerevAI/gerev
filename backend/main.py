from fastapi import FastAPI
from search import search_documents, index_documents
from index import Index
app = FastAPI()


@app.on_event("startup")
async def startup_event():
    Index.create()


@app.post("/example-index")
async def example_index():
    from integrations_api.basic_document import BasicDocument
    from datetime import datetime
    document1 = BasicDocument(title="Hello World", content="This is a test document", author="John Doe",
                              timestamp=datetime.now(), id=1, integration_name="confluence", url="https://www.google.com")
    document2 = BasicDocument(title="Roey is awesome", content="Roey the king", author="John Doe",
                              timestamp=datetime.now(), id=1, integration_name="confluence", url="https://www.google.com")
    index_documents([document1, document2])


@app.get("/search")
async def search(query: str, top_k: int = 5):
    return search_documents(query, top_k)


@app.get("/")
async def root():
    return {"message": "Hello World"}
