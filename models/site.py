from pydantic import BaseModel


class Site(BaseModel):
    id: str = None
    version: str
    multi_site: bool
    url: str = None  # Optional field, initialized to None
    admin_url: str = None  # Optional field, initialized to None

