import json
import urllib.request

lib_name = "torch"

def is_suitable(config, requirements):
    if not requirements.is_contain(lib_name):
        return False
    if not config["cpu_architecture"] == "linux/amd64":
        return False
    if not config["has_gpu"]:
        return False
    if not config["gpu_manufacturer"] == "NVIDIA":
        return False
    return True

def get_image_name(config, requirements):
    response = urllib.request.urlopen(
                "https://hub.docker.com/v2/repositories/pytorch/pytorch/tags/?name=runtime&page_size=100"
            )
    response = json.load(response)["results"]
    image_names = list(map(lambda result: result["name"], response))
    if requirements.is_latest(lib_name):
        return "pytorch/pytorch:latest"
    for im in image_names:
        try:
            version = im.split("-")[0]
            version = version.split(".")
            version = [int(v) for v in version]
            match = requirements.is_match(lib_name, version)
            if match:
                return f"pytorch/pytorch:{im}"
        except (ValueError, TypeError):
            continue
    return "pytorch/pytorch:latest"

def get_image_extras():
    return "RUN apt-get install -y libglib2.0-0"
