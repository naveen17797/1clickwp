from typing import Annotated

import docker
from fastapi import FastAPI, Path, WebSocket
from pydantic import BaseModel
from starlette.responses import HTMLResponse

from models.site import Site
from utils import DB, WordPress

"""
Initialize the db container
"""
db = DB()
db.init_db()


app = FastAPI()
wp = WordPress()


@app.websocket("/create_site")
async def create_site(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Received site creation request")
    # 1. create a wp container
    # 2. if multisite configure it via wp-cli
    url, container_id = await wp.create_instance("6.0.0", True, websocket)
    admin_url = f"{url}/wp-login.php"

    # Instead of returning, send the sentence as a message
    await websocket.send_text("Site created successfully!")
    # You can also send additional information if needed
    await websocket.send_json({"url": url, "admin_url": admin_url})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")






@app.get("/sites")
async def get():
    instances = wp.get_instances()
    sites = []
    for instance in instances:
        attrs = instance.attrs
        version = attrs['Config']['Image'].split(':')[1]
        multi_site = True if 'multisite' in version else False
        url = f"http://localhost:{attrs['HostConfig']['PortBindings']['80/tcp'][0]['HostPort']}"
        site = Site(version=version, multi_site=multi_site, url=url, admin_url=f"{url}/wp-admin", id=attrs['Id'])
        sites.append(site.dict())
    return sites


@app.delete("/sites/{site_id}")
async def delete(site_id: Annotated[str, Path(title="The ID of the site to delete")]):
    wp.delete_instance(site_id)






html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/create_site");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)





# Remove and prune containers on shutdown hook
# Function to stop and remove containers with a specific prefix
def stop_and_remove_containers(prefix: str):
    client = docker.from_env()
    containers = client.containers.list(all=True, filters={"name": f"{prefix}*"})
    for container in containers:
        container.stop()
        container.remove()

@app.on_event("shutdown")
async def cleanup():
    # Stop and remove containers with prefix "1clickwp"
    stop_and_remove_containers("1clickwp")

