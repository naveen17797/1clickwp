import docker
from fastapi import APIRouter, Path, HTTPException

from models.image import Image

router = APIRouter()
client = docker.from_env()


@router.get("/images/{image_id:path}")
async def get_image(image_id: str = Path(..., regex=r'.+')):
    try:
        client.images.get(image_id)
        return Image(id=image_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Item not found")
