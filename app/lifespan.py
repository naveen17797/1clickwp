from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core import Core

core = Core()

@asynccontextmanager
async def lifespan(app:FastAPI):
    core.up()
    core.status()
    core.start_wordpress_instances()
    yield
    core.down()