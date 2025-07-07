from python_on_whales import DockerClient
from pathlib import Path

compose_path = Path(__file__).resolve().parent / "docker-compose.yml"
docker = DockerClient(compose_files=[compose_path])

class Core:
    def __init__(self):
        # Get directory where this script is located
        self.project_dir = Path(__file__).resolve().parent

    def up(self):
        print("Starting services...")
        docker.compose.up(detach=True)
        print("All services started.")

    def down(self):
        print("Stopping services...")
        docker.compose.down(volumes=True)
        print("All services stopped and removed.")

    def restart(self):
        print("Restarting services...")
        self.down()
        self.up()

    def status(self):
        docker.compose.ps()

    def logs(self, follow=True):
        print("Showing logs (Ctrl+C to exit)...")
        docker.compose.logs(follow=follow)
