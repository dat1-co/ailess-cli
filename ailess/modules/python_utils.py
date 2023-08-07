import os
import re
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


class RequirementsParser:

    def __init__(self, requirements):
        if type(requirements) == str:
            req_file = open(requirements, "r")
            requirements = req_file.readlines()
            req_file.close()
        self.requirements = self.parse_all(requirements)

    def parse_line(self, s):
        # Clear
        if s.isspace() or len(s) == 0 or s[0] == '#':
            return '', 'emptyline', []
        s = s.split('#')[0]
        s = s.split(';')[0]
        s = s.split('@')[-1]
        s = s.replace('.*', '')
        s = re.sub(r' *([=><!~]=?) *\*', '', s)
        # Check if local lib
        if os.path.isfile(s):
            return s, 'local', []
        # Check if url
        if s.find('http:') > -1 or s.find('https:') > -1:
            return s, 'url', []
        # Check if no version specified
        if len(re.findall(r'[=><!~]=?', s)) == 0:
            name = re.findall(r'([a-z|0-9|.|_|-]+) *', s)
            if len(name)>0:
                return name[0], 'latest', []
            else:
                return '', 'error', []
        # Fined name and version of lib
        name = re.findall(r'(?:([a-z|0-9|.|_|-]+) *[=><!~]=?)', s)
        version = re.findall(r'(?:(?:[a-z|0-9|.|_|-|\.]+)|,) *([=><!~]=?) *(\b[0-9|.]+)', s)
        version = [[v[0],[int(n) for n in v[1].split('.')]]for v in version]
        if len(name)>0 and len(version)>0:
            return name[0], 'normal', version
        else:
            return '', 'error', []

    def parse_all(self, requirements):
        # "Recursive" reading of requirements and constraints
        reqs = requirements.copy()
        not_all_loaded = True
        pars_start = 0
        while not_all_loaded:
            not_all_loaded = False
            len_reqs = len(reqs)
            for i in range(pars_start, len_reqs):
                req = reqs[i].replace('\n','').lstrip()
                if len(req)>1 and (req[:2]=='-r' or req[:2]=='-c'):
                    not_all_loaded = True
                    path = req[2:].lstrip().rstrip()
                    req_file = open(path, "r")
                    reqs += req_file.readlines()
                    req_file.close()
                pars_start = len_reqs
        
        # Parse requirements
        filtred_reqs = {}
        for i in range(len(reqs)):
            req = reqs[i].replace('\n','').lstrip()
            name, reqtype, version = self.parse_line(req)
            if reqtype == 'normal' or reqtype == 'latest':
                filtred_reqs[name] = version
        return filtred_reqs

    @staticmethod
    def compare(val1, sign, val2):
        if sign == '==' or sign == '~=' or sign == '~':
            return val1 == val2
        elif sign == '!=':
            return not (val1 == val2)
        elif sign == '>=':
            return val1 >= val2
        elif sign == '<=':
            return val1 <= val2
        elif sign == '>':
            return val1 > val2
        elif sign == '<':
            return val1 < val2

    def is_contain(self, name):
        if name in self.requirements:
            return True
        else:
            return False
        
    def is_latest(self, name):
        if name in self.requirements and len(self.requirements[name]) == 0:
            return True
        else:
            return False
         
    def is_match(self, name, version):
        # If latest any version
        if not self.is_contain(name):
            return False
        targets = self.requirements[name]
        if len(targets) == 0 or len(version) == 0:
            return True
        for sign, t in targets:
            if not self.compare(version, sign, t):
                return False
        return True

