import uvicorn
from fastapi import FastAPI

from app.core import CoreManager

app = FastAPI(
    title="Modular FastAPI Application",
    version="1.0.0",
)

core_manager = CoreManager()

@app.on_event("startup")
async def startup():
    # بارگذاری ماژول‌ها در شروع اپ
    core_manager.load_modules()

@app.on_event("shutdown")
async def shutdown():
    # می‌توانید cleanup ماژول‌ها را اینجا انجام دهید
    pass

@app.get("/")
def root():
    return {"message": "Welcome to Modular FastAPI App"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
