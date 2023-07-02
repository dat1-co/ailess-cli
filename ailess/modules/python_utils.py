import os
import shutil
from yaspin import yaspin

from pipreqs.pipreqs import get_all_imports, get_pkg_names, get_import_local, get_imports_info

def find_pip_command():
    """
    Finds the appropriate pip command based on availability.
    Returns 'pip3' if available, otherwise 'pip'.
    """
    if shutil.which('pip3') is not None:
        return 'pip3'
    elif shutil.which('pip') is not None:
        return 'pip'
    else:
        return None
def ensure_requirements_exists():
    if not os.path.exists("requirements.txt"):
        print("requirements.txt not found. Generating using pip freeze. We recommend writing your own requirements.txt as this approach will include all dependencies, including those that are not used.")
        generate_requirements_file("./")


def get_libs(project_path):
    candidates = get_all_imports(project_path, encoding=None, extra_ignore_dirs=None, follow_links=None)
    candidates = get_pkg_names(candidates)
    pypi_server = "https://pypi.python.org/pypi/"
    local = get_import_local(candidates, encoding=None)

    difference = [
        x
        for x in candidates
        if x.lower() not in [y for x in local for y in x["exports"]]
        and x.lower() not in [x["name"] for x in local]
    ]

    imports = local + get_imports_info(difference, proxy=None, pypi_server=pypi_server)
    imports = sorted(imports, key=lambda x: x["name"].lower())
    return imports


def generate_requirements_file(project_path):
    from ailess.modules.cli_utils import run_command_in_working_directory
    with yaspin(text="    generating requirements.txt") as spinner:
        pip_command = find_pip_command()

        if pip_command is None:
            spinner.fail("pip not found. please install pip or create a valid requirements.txt file")
            return

        run_command_in_working_directory("{} freeze > requirements.txt".format(pip_command), spinner)
