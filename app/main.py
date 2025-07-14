import base64
import os
import re
from pathlib import Path

from docker import errors as docker_errors
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from python_on_whales import docker

from app.core import Core
from app.database import Database
from app.lifespan import lifespan

app = FastAPI(lifespan=lifespan)
core = Core()
database = Database()

TRAEFIK_CERT_RESOLVER = "myresolver"
TRAEFIK_ENTRYPOINT_WEB = "web"
TRAEFIK_ENTRYPOINT_WEBSECURE = "websecure"
DB_CONTAINER_NAME = "1clickwp_db"
DOCKER_NETWORK = "1clickwp"
WORDPRESS_CONTAINER_PREFIX = "1clickwp_wordpress_"


# -----------------------------
# Utility Functions
# -----------------------------

def generate_site_id(name: str) -> str:
    b64 = base64.urlsafe_b64encode(name.encode('utf-8')).decode()
    return b64.rstrip("=")  # optional: remove padding for cleaner URL

def sanitize_name(name: str) -> str:
    # Keep only letters and hyphens
    return re.sub(r'[^a-zA-Z0-9\-]', '', name)

def get_container_name(site_id: str) -> str:
    return f"{WORDPRESS_CONTAINER_PREFIX}{site_id}"

def site_exists(site_id: str) -> bool:
    expected_name = get_container_name(site_id)
    return any(
        container.name == expected_name
        for container in docker.container.list(all=True)
    )



def traefik_labels(site_name: str, container_port: int = 8080) -> dict:
    domain = f"{site_name}.localhost"
    router = f"{site_name}-router"
    middleware = f"{site_name}-headers"

    return {
        "traefik.enable": "true",
        f"traefik.http.routers.{router}.rule": f"Host(`{domain}`)",
        f"traefik.http.routers.{router}.entrypoints": TRAEFIK_ENTRYPOINT_WEBSECURE,
        f"traefik.http.routers.{router}.tls": "true",
        f"traefik.http.routers.{router}.tls.certresolver": TRAEFIK_CERT_RESOLVER,
        f"traefik.http.routers.{router}.middlewares": middleware,
        f"traefik.http.services.{router}.loadbalancer.server.port": str(container_port),

        # HTTP → HTTPS Redirect
        f"traefik.http.routers.{router}-http.rule": f"Host(`{domain}`)",
        f"traefik.http.routers.{router}-http.entrypoints": TRAEFIK_ENTRYPOINT_WEB,
        f"traefik.http.routers.{router}-http.middlewares": "redirect-to-https",
        f"traefik.http.routers.{router}-http.service": "noop@internal",
        "traefik.http.middlewares.redirect-to-https.redirectscheme.scheme": "https",

        # Secure Headers
        f"traefik.http.middlewares.{middleware}.headers.SSLRedirect": "true",
        f"traefik.http.middlewares.{middleware}.headers.STSSeconds": "31536000",
        f"traefik.http.middlewares.{middleware}.headers.SSLHost": domain,
        f"traefik.http.middlewares.{middleware}.headers.STSIncludeSubdomains": "true",
        f"traefik.http.middlewares.{middleware}.headers.STSPreload": "true",
        f"traefik.http.middlewares.{middleware}.headers.frameDeny": "true",
        f"traefik.http.middlewares.{middleware}.headers.customResponseHeaders.X-Frame-Options": "SAMEORIGIN",
        f"traefik.http.middlewares.{middleware}.headers.contentTypeNosniff": "true",
        f"traefik.http.middlewares.{middleware}.headers.browserXSSFilter": "true",
    }

def stop_all_1clickwp_containers() -> list:
    stopped = []
    for container in docker.container.list():
        if container.name.startswith(WORDPRESS_CONTAINER_PREFIX):
            try:
                docker.container.stop(container.name)
                stopped.append(container.name)
            except Exception as e:
                print(f"Error stopping {container.name}: {e}")
    return stopped

def start_all_1clickwp_containers() -> list:
    started = []
    for container in docker.container.list(all=True):
        if container.name.startswith(WORDPRESS_CONTAINER_PREFIX):
            try:
                docker.container.start(container.name)
                started.append(container.name)
            except Exception as e:
                print(f"Error starting {container.name}: {e}")
    return started






# -----------------------------
# API Routes
# -----------------------------

@app.get("/sites")
def list_sites():
    containers = docker.container.list(all=True)
    result = []

    for c in containers:
        if c.name.startswith(WORDPRESS_CONTAINER_PREFIX):
            site_id = c.name.replace(WORDPRESS_CONTAINER_PREFIX, "")
            site_name = c.config.labels.get('1clickwp.site_name', site_id)
            domain = f"{site_name}.localhost"
            result.append({
                "name": site_name,
                "domain": domain,
                "container": c.name
            })

    return result


@app.post("/sites")
def create_site(name: str):
    def prepare_site_dir(container_name: str) -> str:
        site_path = f"./sites/{container_name}"  # Adjust this base path as needed
        os.makedirs(site_path, exist_ok=True)
        os.chmod(site_path, 0o777)  # Full read/write/execute for all
        return site_path


    name = sanitize_name(name)
    site_id = generate_site_id(name)
    container_name = get_container_name(site_id)
    site_path = os.path.join( "./sites", name)

    if site_exists(site_id):
        raise HTTPException(status_code=400, detail="Site already exists")

    database.create(container_name)
    prepare_site_dir(name)
    try:
        docker.container.run(
            image="bitnami/wordpress:latest",
            name=container_name,
            networks=[DOCKER_NETWORK],
            envs={
                "WORDPRESS_DATABASE_HOST": DB_CONTAINER_NAME,
                "WORDPRESS_DATABASE_NAME": container_name,
                "WORDPRESS_DATABASE_USER": "root",
                "WORDPRESS_DATABASE_PASSWORD": "local",
                "WORDPRESS_USERNAME": "admin",
                "WORDPRESS_PASSWORD": "password",
            },
            labels={
                **traefik_labels(name),
                "1clickwp.site_name": name
            },
            volumes=[(site_path +'/', '/bitnami/wordpress'),
                     ('./deps/scripts/wp-init.sh', '/docker-entrypoint-init.d/wp-init.sh'),
                     ('./deps/mu-plugins','/tmp/mu-plugins'),
                     ],
            detach=True
        )

    except docker_errors.APIError as e:
        raise HTTPException(status_code=500, detail=f"Container start failed: {e.explanation}")

    return {
        "message": f"Site created at https://{name}.localhost",
        "container": container_name
    }

@app.delete("/sites/{name}")
def delete_site(name: str):
    site_id = generate_site_id(sanitize_name(name))
    container_name = get_container_name(site_id)

    try:
        docker.container.remove(container_name, force=True)
        return {"message": f"Site '{name}' deleted"}
    except docker_errors.NotFound:
        raise HTTPException(status_code=404, detail="Site not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# -----------------------------
# Static File Hosting
# -----------------------------

static_path = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
def serve_index():
    return FileResponse(static_path / "index.html")