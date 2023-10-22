from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from utils import DB, WordPress

db = DB()
db.init_db()

app = FastAPI()


class Site(BaseModel):
    version: str
    multi_site: bool
    url: str = None  # Optional field, initialized to None
    admin_url: str = None  # Optional field, initialized to None

@app.post("/sites")
async def create(site: Site):
    # steps
    # 1. create a wp container
    # 2. if multisite configure it via wp-cli
    wp = WordPress()
    url =  wp.create_instance(site.version, site.multi_site)
    admin_url = f"{url}/wp-login.php"
    site.url = url
    site.admin_url = admin_url
    return site


@app.get("/")
async def root():
    return []
