import os
import docker


class BaseContainerManager:
    def __init__(self, name, image, ports=None, volumes=None, environment=None, labels=None):
        self.client = docker.from_env()
        self.name = name
        self.image = image
        self.ports = ports or {}
        self.volumes = volumes or {}
        self.environment = environment or {}
        self.labels = labels or {}

    def container_exists(self):
        try:
            return self.client.containers.get(self.name)
        except docker.errors.NotFound:
            return None

    def container_is_running(self, container):
        container.reload()
        return container.status == "running"

    def remove_container(self, container):
        print(f"Removing container {container.name}")
        container.remove(force=True)

    def pull_image(self):
        print(f"Pulling image {self.image}...")
        self.client.images.pull(self.image)
        print("Image pulled.")

    def run_container(self):
        print(f"Starting container: {self.name}")
        self.client.containers.run(
            self.image,
            name=self.name,
            detach=True,
            restart_policy={"Name": "always"},
            ports=self.ports,
            volumes=self.volumes,
            environment=self.environment,
            labels=self.labels
        )

    def ensure_running(self):
        container = self.container_exists()
        if container:
            if self.container_is_running(container):
                print(f"Container '{self.name}' already running.")
                return
            else:
                print(f"Container '{self.name}' exists but not running.")
                self.remove_container(container)

        self.pull_image()
        self.run_container()
