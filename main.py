from fastapi import FastAPI
from pydantic import BaseModel

from utils import DB, WordPress

db = DB()
db.init_db()

app = FastAPI()


class Site(BaseModel):
    version: str
    multi_site: bool


@app.post("/sites")
async def create(site: Site):
    # steps
    # 1. create a wp container
    # 2. if multisite configure it via wp-cli
    wp = WordPress()
    return wp.create_instance(site.version, site.multi_site)



@app.get("/")
async def root():
    return []
