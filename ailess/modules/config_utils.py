import json
import os

def ensure_workdir_exists():
    if not os.path.exists('.ailess'):
        os.mkdir('.ailess')

def save_config(config):
    ensure_workdir_exists()
    with open('.ailess/config.json', 'w') as f:
        json.dump(config, f, indent=4)
