import os
from pathlib import Path

def get_project_root() -> Path:
    return Path(__file__).parent.parent

def get_resource_dir() -> Path:
    root = get_project_root()
    inputs = root.parent.parent.joinpath("inputs")
    return inputs 
