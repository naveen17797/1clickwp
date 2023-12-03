from typing import Annotated

from fastapi import APIRouter,Path

from models.site import Site
from utils import WordPress

router = APIRouter()
wp = WordPress()



@router.post("/sites")
async def create(site: Site):
    # steps
    # 1. create a wp container
    # 2. if multisite configure it via wp-cli
    url, id =  wp.create_instance(site.version, site.multi_site, site.volume_bindings)
    admin_url = f"{url}/wp-login.php"
    site.url = url
    site.id = id
    site.admin_url = admin_url
    return site

@router.get("/sites")
async def get():
    instances = wp.get_instances()
    sites = []
    for instance in instances:
        attrs = instance.attrs
        name = attrs['Name']
        version = attrs['Config']['Image'].split(':')[1]
        multi_site = True if 'multi_site' in name else False
        url = f"http://localhost:{attrs['HostConfig']['PortBindings']['80/tcp'][0]['HostPort']}"
        site = Site(version=version, multi_site=multi_site, url=url, admin_url=f"{url}/wp-admin", id=attrs['Id'], volume_bindings=[])
        sites.append(site.dict())
    return sites

@router.delete("/sites/{site_id}")
async def delete( site_id: Annotated[str, Path(title="The ID of the site to delete")]):
    wp.delete_instance(site_id)
