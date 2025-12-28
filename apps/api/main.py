from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/health")
def health():
    return {"time": datetime.utcnow().isoformat(), "code": 0, "message": "OK", "data": {"status": "up"}}

@app.get("/hello")
def hello():
    return {"time": datetime.utcnow().isoformat(), "code": 0, "message": "OK", "data": {"hello": "tobit-spa-ai"}}
