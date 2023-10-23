from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from utils import DB, WordPress

db = DB()
db.init_db()

app = FastAPI()


class Site(BaseModel):
    id:str = None
    version: str
    multi_site: bool
    url: str = None  # Optional field, initialized to None
    admin_url: str = None  # Optional field, initialized to None
wp = WordPress()

@app.post("/sites")
async def create(site: Site):
    # steps
    # 1. create a wp container
    # 2. if multisite configure it via wp-cli
    url =  wp.create_instance(site.version, site.multi_site)
    admin_url = f"{url}/wp-login.php"
    site.url = url
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
        site = Site(version=version, multi_site=multi_site, url=url, admin_url=f"{url}/wp-admin", id=attrs['Name'])
        sites.append(site.dict())
    return sites


@app.get("/")
async def root():
    return []
