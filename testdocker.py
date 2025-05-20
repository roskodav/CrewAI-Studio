# test_docker.py
import docker

try:
    client = docker.DockerClient(base_url="npipe:////./pipe/docker_engine")
    print("Docker version:", client.version())
    print("Containers:", client.containers.list())
except Exception as e:
    print("Docker connection failed:", e)