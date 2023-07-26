import os

from pipreqs.pipreqs import get_all_imports, get_pkg_names, get_import_local, get_imports_info


def ensure_requirements_exists():
    if not os.path.exists("requirements.txt"):
        print("WARNING: requirements.txt not found. We will try to generate one for you. This is an experimental feature and will not work in all cases. Please double-check the generated file.")
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
    libs = get_libs(project_path)
    file_path = os.path.join(project_path, "requirements.txt")
    requirements = ""
    for lib in libs:
        requirements += "{}=={}\n".format(lib["name"], lib["version"])
    with open(file_path, "w") as file:
        file.write(requirements)
