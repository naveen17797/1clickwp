import docker
from fastapi import FastAPI
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from utils import DB
from routers import sites, images


app = FastAPI()
origins = ["http://localhost:4200"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sites.router)
app.include_router(images.router)
app.mount("/ui", StaticFiles(directory="ui/dist/ui/"))

@app.get("/")
async def root():
    return RedirectResponse(url="/ui/index.html")

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