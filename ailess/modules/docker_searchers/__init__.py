from ailess.modules.docker_searchers import tensorflow_amd64_nvidia
from ailess.modules.docker_searchers import pytorch_amd64_nvidia
from ailess.modules.docker_searchers import python_basic

searchers = [tensorflow_amd64_nvidia, pytorch_amd64_nvidia, python_basic]

def get_sercher_from_config(config, requirements):
    for searcher in searchers:
        if searcher.is_suitable(config, requirements):
            return searcher