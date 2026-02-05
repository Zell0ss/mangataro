from api.main import app
import uvicorn

# Optional debug route
@app.get("/debug")
def debug():
    return {"status": "running from api.main"}

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8888,
        reload=True
    )