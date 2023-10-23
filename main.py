import docker
from fastapi import FastAPI
from utils import DB
from routers import sites


app = FastAPI()
app.include_router(sites.router)

@app.get("/")
async def root():
    return []

# Remove and prune containers on shutdown hook
# Function to stop and remove containers with a specific prefix
def stop_and_remove_containers(prefix: str):
    client = docker.from_env()
    containers = client.containers.list(all=True, filters={"name": f"{prefix}*"})
    for container in containers:
        container.stop()
        container.remove()

@app.on_event("shutdown")
async def cleanup():
    # Stop and remove containers with prefix "1clickwp"
    stop_and_remove_containers("1clickwp")

@app.on_event("startup")
async def cleanup():
    # Remove orphaned containers.
    stop_and_remove_containers("1clickwp")
    db = DB()
    db.init_db()