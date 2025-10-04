from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import game, health, debug

# import pydevd_pycharm
# pydevd_pycharm.settrace(
#     'host.docker.internal',  # or your host IP
#     port=5690,               # must match the PyCharm Debug Server config
#     stdout_to_server=True,
#     stderr_to_server=True,
#     suspend=False            # set True to pause immediately on connect
# )

app = FastAPI(
    title="PlotPlay API",
    description="AI-driven text adventure engine",
    version="0.1.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(game.router, prefix="/api/game", tags=["game"])
app.include_router(debug.router, prefix="/api/debug", tags=["debug"]) # Include the debug router

@app.get("/")
def root():
    return {"message": "PlotPlay API", "version": "0.1.0"}
