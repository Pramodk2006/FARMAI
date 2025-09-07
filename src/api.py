from fastapi import FastAPI

app = FastAPI(title="Agricultural AI System API")

@app.get("/")
async def root():
    return {"message": "Agricultural AI System API is running"}
