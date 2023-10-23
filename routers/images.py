import math

import docker
from fastapi import APIRouter, Path, HTTPException

from models.image import Image

router = APIRouter()
client = docker.from_env(timeout=3600)


@router.get("/images/{image_id:path}")
async def get_image(image_id: str = Path(..., regex=r'.+')):
    try:
        client.images.get(image_id)
        return Image(id=image_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Item not found")


@router.post("/images/{image_id:path}/pulls")
async def pull_image(image_id: str = Path(..., regex=r'.+')):
    try:
        name, tag = image_id.split(":")
        client.images.pull(name, tag)
        return Image(id=image_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error in pulling image")
