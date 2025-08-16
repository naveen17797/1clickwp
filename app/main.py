import base64
import json
import os
import re
import shutil
from pathlib import Path
import time, requests
from docker import errors as docker_errors
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
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


# Get base directory (directory of this current script)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.post("/sites")
def create_site(name: str, wordpress_image_name:str):
    def prepare_site_dir(container_name: str) -> str:
        site_path = os.path.join(BASE_DIR, "sites", container_name)
        os.makedirs(site_path, exist_ok=True)
        os.chmod(site_path, 0o777)  # Full read/write/execute for all
        return site_path

    name = sanitize_name(name)
    site_id = generate_site_id(name)
    container_name = get_container_name(site_id)

    if site_exists(site_id):
        raise HTTPException(status_code=400, detail="Site already exists")

    site_path = prepare_site_dir(name)

    # Create the DB for the site
    database.create(container_name)

    try:
        volumes = [
            (site_path, '/bitnami/wordpress'),
            (os.path.join(BASE_DIR, 'deps', 'scripts', 'wp-init.sh'), '/docker-entrypoint-init.d/wp-init.sh'),
            (os.path.join(BASE_DIR, 'deps', 'mu-plugins'), '/tmp/mu-plugins'),
        ]
        print(volumes)
        docker.container.run(
            image=wordpress_image_name,
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
            volumes=volumes,
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
    site_path = os.path.join(BASE_DIR, "sites", name)
    database.delete(container_name)
    try:
        docker.container.remove(container_name, force=True)
        print(site_path)
        shutil.rmtree(site_path, ignore_errors=True)
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




# Simple in-memory cache
_cache = {
    "data": None,
    "timestamp": 0
}
CACHE_TTL = 3600  # seconds

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


CACHE_FILENAME = os.path.join(os.path.dirname(__file__), "wp_tags_cache.json")

def fetch_wp_tags():
    # If cache exists, load from file
    if os.path.exists(CACHE_FILENAME):
        with open(CACHE_FILENAME, "r", encoding="utf-8") as f:
            try:
                tags = json.load(f)
                if isinstance(tags, list) and all(isinstance(t, str) for t in tags):
                    return tags
            except json.JSONDecodeError:
                pass  # If cache is corrupt, fall back to fetch

    # Fetch from Docker Hub
    url = "https://registry.hub.docker.com/v2/repositories/bitnami/wordpress/tags?page_size=100"
    tags = []

    while url:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for t in data.get("results", []):
            name = t.get("name")
            if SEMVER_RE.match(name):
                tags.append(name)
        url = data.get("next")

    # Sort tags (descending semantic version order)
    tags.sort(key=lambda v: list(map(int, v.split("."))), reverse=True)

    # Save to cache
    with open(CACHE_FILENAME, "w", encoding="utf-8") as f:
        json.dump(tags, f, indent=2)

    return tags

@app.get("/wp-tags")
async def get_wp_tags():
    try:
        tags = fetch_wp_tags()
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    return JSONResponse(content=tags)






@app.get("/wait-for-site")
def wait_for_site(name: str, timeout: int = 90, interval: int = 3):
    domain = f"{name}.localhost"  # change to your domain pattern
    url = f"https://{domain}"

    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            r = requests.head(url, verify=False, timeout=2)
            if r.status_code < 500:  # consider <500 as "ready"
                return {"ready": True}
        except Exception:
            pass
        time.sleep(interval)
    return {"ready": False}
