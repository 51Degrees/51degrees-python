# Prints, as JSON, the flags an on-premise package's setup.py gives the
# compiler and the linker on a platform, for ci/native-warnings.Tests.ps1.
#
#   python native-build-flags.py <setup.py> <sys.platform>
#
# setup.py is run as it is, with the environment this is run in, so its
# reading of _51DEGREES_WARNINGS_AS_ERRORS is what is tested. setup(),
# Extension, the setuptools and Cython build commands and the copy of the
# native source are replaced, so nothing is built, copied or installed, and
# neither setuptools, Cython nor the native source is needed.

import json
import os
import shutil
import sys
import types

setup_py = os.path.abspath(sys.argv[1])
target_platform = sys.argv[2]


class Command:
    pass


def module(name, **attributes):
    created = types.ModuleType(name)
    created.__dict__.update(attributes)
    sys.modules[name] = created
    return created


found = {}


def extension(name, **options):
    return dict(options, name=name)


def setup(**options):
    found["extensions"] = [
        {
            "name": e["name"],
            "compile": e.get("extra_compile_args", []),
            "link": e.get("extra_link_args", []),
        }
        for e in options.get("ext_modules", [])
    ]
    found["libraries"] = [
        {"name": name, "compile": info.get("cflags", [])}
        for name, info in options.get("libraries", [])
    ]


module("setuptools", setup=setup, Extension=extension)
module("setuptools.command")
module("setuptools.command.develop")
module("setuptools.command.build_clib", build_clib=Command)
module("distutils", sysconfig=module("distutils.sysconfig"))
module("Cython")
module("Cython.Distutils", build_ext=Command)

shutil.copytree = lambda *args, **kwargs: None
shutil.rmtree = lambda *args, **kwargs: None

# setup.py stops when it finds no native source to copy. The flags don't
# depend on it, and the CI script tests check out no submodule, so the
# source folders read as present.
found_dir = os.path.isdir
os.path.isdir = lambda path: found_dir(path) or os.path.normpath(
    path).endswith(os.path.join("cxx", "src"))
sys.platform = target_platform

os.chdir(os.path.dirname(setup_py))
with open(setup_py, encoding="utf-8") as source:
    code = compile(source.read(), setup_py, "exec")
exec(code, {"__name__": "__main__", "__file__": setup_py})

print(json.dumps(found))
