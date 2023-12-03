from typing import List

from pydantic import BaseModel


class VolumeBinding(BaseModel):
    host_path: str
    container_path: str

class Site(BaseModel):
    id:str = None
    version: str
    multi_site: bool
    volume_bindings: List[VolumeBinding]
    url: str = None  # Optional field, initialized to None
    admin_url: str = None  # Optional field, initialized to None