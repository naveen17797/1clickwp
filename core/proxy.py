import os
import docker

class Proxy:
    CONTAINER_NAME = "1clickwp_proxy"
    TRAEFIK_IMAGE = "traefik:v3.0"

    def __init__(self):
        self.client = docker.from_env()
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.proxy_yml, self.dynamic_yml = self.get_config_paths()

    def init(self):
        """Initialize Traefik setup: pull image and ensure container is running"""
        self.pull_image()
        self.ensure_container_running()

    def pull_image(self):
        """Pull the Traefik image (if not already pulled)"""
        if not self.client.images.get(self.TRAEFIK_IMAGE):
            print(f"Pulling image {self.TRAEFIK_IMAGE}...")
            self.client.images.pull(self.TRAEFIK_IMAGE)
            print("Image pulled.")

    def get_config_paths(self):
        """Return absolute paths to static and dynamic config files"""
        proxy_yml = os.path.join(self.base_dir, "traefik.yml")
        dynamic_yml = os.path.join(self.base_dir, "dynamic.yml")
        return proxy_yml, dynamic_yml

    def container_exists(self):
        """Check if container with name exists"""
        try:
            return self.client.containers.get(self.CONTAINER_NAME)
        except docker.errors.NotFound:
            return None

    def container_is_running(self, container):
        """Check if the container is currently running"""
        container.reload()
        return container.status == "running"

    def remove_container(self, container):
        """Force-remove existing container"""
        print(f"Removing existing container: {container.name}")
        container.remove(force=True)

    def run_container(self):
        """Run a new Traefik container with appropriate settings"""
        print(f"Starting new Traefik container: {self.CONTAINER_NAME}")
        self.client.containers.run(
            self.TRAEFIK_IMAGE,
            name=self.CONTAINER_NAME,
            detach=True,
            restart_policy={"Name": "always"},
            ports={
                "80/tcp": 80,
                "443/tcp": 443
            },
            volumes={
                "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "ro"},
                self.proxy_yml: {"bind": "/etc/traefik/traefik.yml", "mode": "ro"},
                self.dynamic_yml: {"bind": "/etc/traefik/dynamic.yml", "mode": "ro"},
            }
        )

    def ensure_container_running(self):
        """Ensure the Traefik container is running; replace if needed"""
        container = self.container_exists()

        if container:
            if self.container_is_running(container):
                print(f"Container '{self.CONTAINER_NAME}' is already running.")
                return
            else:
                print(f"Container '{self.CONTAINER_NAME}' exists but is not running.")
                self.remove_container(container)
        else:
            print(f"Container '{self.CONTAINER_NAME}' does not exist.")

        self.run_container()
