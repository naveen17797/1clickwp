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
    url, id, table_prefix =  wp.create_instance(site.version, site.multi_site, site.volume_bindings, site.memory, site.cpu, site.wp_debug)
    admin_url = f"{url}/wp-login.php"
    site.url = url
    site.id = id
    site.admin_url = admin_url
    site.phpmyadmin_url = f"http://localhost:9999/index.php?route=/database/structure&db=1clickwp_db&prefix={table_prefix}"
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
        phpmyadmin_url = f"http://localhost:9999/index.php?route=/database/structure&db=1clickwp_db&prefix={instance.labels['table_prefix']}"
        site = Site(version=version, multi_site=multi_site, url=url, admin_url=f"{url}/wp-admin", id=attrs['Id'], volume_bindings=[], phpmyadmin_url=phpmyadmin_url)
        sites.append(site.dict())
    return sites

@router.delete("/sites/{site_id}")
async def delete( site_id: Annotated[str, Path(title="The ID of the site to delete")]):
    wp.delete_instance(site_id)
