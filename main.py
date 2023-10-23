from typing import Annotated
import docker
from fastapi import FastAPI, Path

from models.site import Site
from utils import DB, WordPress

app = FastAPI()

wp = WordPress()

@app.post("/sites")
async def create(site: Site):
    # steps
    # 1. create a wp container
    # 2. if multisite configure it via wp-cli
    url, id =  wp.create_instance(site.version, site.multi_site)
    admin_url = f"{url}/wp-login.php"
    site.url = url
    site.id = id
    site.admin_url = admin_url
    return site

@app.get("/sites")
async def get():
    instances = wp.get_instances()
    sites = []
    for instance in instances:
        attrs = instance.attrs
        version = attrs['Config']['Image'].split(':')[1]
        multi_site = True if 'multisite' in version else False
        url = f"http://localhost:{attrs['HostConfig']['PortBindings']['80/tcp'][0]['HostPort']}"
        site = Site(version=version, multi_site=multi_site, url=url, admin_url=f"{url}/wp-admin", id=attrs['Id'])
        sites.append(site.dict())
    return sites

@app.delete("/sites/{site_id}")
async def delete( site_id: Annotated[str, Path(title="The ID of the site to delete")]):
    wp.delete_instance(site_id)



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