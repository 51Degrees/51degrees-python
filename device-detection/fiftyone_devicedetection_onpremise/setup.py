# *********************************************************************
# This Original Work is copyright of 51 Degrees Mobile Experts Limited.
# Copyright 2026 51 Degrees Mobile Experts Limited, Davidson House,
# Forbury Square, Reading, Berkshire, United Kingdom RG1 3EU.
#
# This Original Work is licensed under the European Union Public Licence
# (EUPL) v.1.2 and is subject to its terms as set out below.
#
# If a copy of the EUPL was not distributed with this file, You can obtain
# one at https://opensource.org/licenses/EUPL-1.2.
#
# The 'Compatible Licences' set out in the Appendix to the EUPL (as may be
# amended by the European Commission) shall be deemed incompatible for
# the purposes of the Work and the provisions of the compatibility
# clause in Article 5 of the EUPL shall not apply.
#
# If using the Work as, or as part of, a network application, by
# including the attribution notice(s) required under Article 5 of the EUPL
# in the end user terms of the application under an appropriate heading,
# such notice(s) shall fulfill the requirements of that article.
# *********************************************************************

"""
setup.py file for SWIG
"""
import sys
import platform
from setuptools import setup, Extension
from setuptools.command import develop
from distutils import sysconfig
from Cython.Distutils import build_ext
from glob import glob
import os
import io

# Read a text file and return the content as a string.
def read(file_name):

    """Read a text file and return the content as a string."""
    try:
        with io.open(
            os.path.join(os.path.dirname(__file__), file_name), encoding="utf-8"
        ) as f:
            return f.read().strip()
    except:
        return "0.0.0"

def get_version():

    version = None

    # Try to get the correct version from platform.
    is_64bits = sys.maxsize > 2**32
    if is_64bits:
        if 'Windows' in platform.system():
            version = "win_64_"
        if 'Linux' in platform.system():
            version = "linux_64_"
        if 'Darwin' in platform.system():
            version = "darwin_64_"
    else:
        if 'Windows' in platform.system():
            version = "win_32_"
        if 'Linux' in platform.system():
            version = "linux_32_"
        if 'Darwin' in platform.system():
            # No 32 bit python on Mac
            version = None
            raise Exception("Sorry, No 32 bit Python on Mac")

    python_version = str(sys.version_info[0])
    return version + python_version

class NoSuffixBuilder(build_ext):
    def get_ext_filename(self, ext_name):
        filename = super().get_ext_filename(ext_name)
        suffix = sysconfig.get_config_var('EXT_SUFFIX')
        if suffix is None:
            suffix = sysconfig.get_config_var('SO')

        print("**" + filename + "**\r\n")
        print("**" + suffix + "**\r\n")

        # Get the version from the suffix.
        version = get_version()

        ext = os.path.splitext(filename)[1]

        if self.inplace:
            return "./" + filename.replace(suffix, "") + ext
        else:
            return filename.replace(suffix, "") + ext

define_macros = []
extra_compile_args = []
extra_link_args = []
# Extra compilation flags for C library
cflags = []

if sys.platform != "win32":
    extra_compile_args.extend([
        '-fPIC',
        '-std=gnu++17',
        '-Wall',
        # '-Werror'
    ])
    cflags.extend([
        '-std=gnu11',
        '-Wall',
        # '-Werror',
        '-Wno-strict-prototypes',
        '-Wno-unused-variable',
        '-Wno-missing-braces',
        '-Wno-strict-aliasing'
    ])


if sys.platform == "win32":
    extra_compile_args.extend([
        '/std:c++17',
        '/D_CRT_SECURE_NO_WARNINGS',
        '/D_UNICODE',
        '/DUNICODE',
        '/W4',
        # '/WX',
        '/wd4127',
        '/wd4456',
        '/wd4701',
        '/wd4703',
        '/wd4706'
    ])
    cflags.extend([
        '/D_CRT_SECURE_NO_WARNINGS',
        '/D_UNICODE',
        '/DUNICODE',
        '/W4',
        # '/WX'
    ])
    extra_link_args.extend([
        '/WX'
    ])

if sys.platform == "linux":
    extra_link_args.extend([
        '-latomic'
    ])

if sys.platform == 'darwin':
    # This is flaged in CPython
    extra_compile_args.extend([
        '-DGCC_ENABLE_CPP_EXCEPTIONS=YES'
    ])
    if sys.version_info[0] == 3 and sys.version_info[1] == 8:
        extra_compile_args.extend([
            '-Wno-deprecated-declarations'
    ])
    cflags.extend([
        '-Wno-atomic-alignment'
    ])

DeviceDetectionHashEngineModule = Extension('_DeviceDetectionHashEngineModule',
        sources=[
        # Python Wrapper
        # "fiftyone_devicedetection_onpremise/hash_python.i"
        "src/fiftyone_devicedetection_onpremise/hash_python_wrap.cxx"
        ],
        define_macros=define_macros,
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
        language='c++',
    )

cpplib = ('cpplib', {
        'sources': [
            # Common C++
            *glob("src/fiftyone_devicedetection_onpremise/cxx/src/common-cxx/*.cpp"),
            # Device Detection C++
            *glob("src/fiftyone_devicedetection_onpremise/cxx/src/*.cpp"),
            # Hash C++
            *glob("src/fiftyone_devicedetection_onpremise/cxx/src/hash/*.cpp"),
            ],
        'cflags': extra_compile_args
    })

clib = ('clib', {
        'sources': [
            # Common C
            *glob("src/fiftyone_devicedetection_onpremise/cxx/src/common-cxx/*.c"),
            # Device Detection C
            *glob("src/fiftyone_devicedetection_onpremise/cxx/src/*.c"),
            # Hash C
            *glob("src/fiftyone_devicedetection_onpremise/cxx/src/hash/*.c"),
        ],
        'cflags': cflags
    })

setup(
    cmdclass={"build_ext": NoSuffixBuilder},
    name="fiftyone_devicedetection_onpremise",
    version=read("version.txt"),
    author="51Degrees Engineering",
    author_email="engineering@51degrees.com",
    description = """This project contains 51Degrees Device Detection OnPremise engine that can be used with the 51Degrees Pipeline API. The Pipeline is a generic web request intelligence and data processing solution with the ability to add a range of 51Degrees and/or custom plug ins (Engines)""",
    long_description=read("readme.md"),
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    license="EUPL-1.2",
    libraries=[cpplib, clib],
    ext_package="fiftyone_devicedetection_onpremise",
    ext_modules=[DeviceDetectionHashEngineModule],
    py_modules=["fiftyone_devicedetection_onpremise"],
    packages=["fiftyone_devicedetection_onpremise"],
    package_dir={"": "src"},
    install_requires=["fiftyone_devicedetection_shared", "fiftyone_pipeline_engines_fiftyone"],
)
