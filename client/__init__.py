import docker
from docker.client import DockerClient

_client = docker.from_env()
def get_docker_client()->DockerClient:
    return _client