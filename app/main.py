from fastapi import FastAPI
from fastapi.params import Body
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
def root():
    return {"senac": "Pós Full-Stack"}
