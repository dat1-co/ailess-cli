import json
import os


def ensure_workdir_exists():
    if not os.path.exists(".ailess"):
        os.mkdir(".ailess")


def save_config(config):
    ensure_workdir_exists()
    with open(".ailess/config.json", "w") as f:
        json.dump(config, f, indent=4)


def load_config():
    if not os.path.exists(".ailess/config.json"):
        print('No .ailess/config.json file found. Please run "ailess init" first.')
        exit(1)
    with open(".ailess/config.json", "r") as f:
        return json.load(f)
