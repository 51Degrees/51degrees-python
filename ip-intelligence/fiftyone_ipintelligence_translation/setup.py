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

import setuptools
import io
import os
import shutil


def read(file_name):

    """Read a text file and return the content as a string."""
    try:
        with io.open(
            os.path.join(os.path.dirname(__file__), file_name), encoding="utf-8"
        ) as f:
            return f.read().strip()
    except Exception:
        return "0.0.0"


def stage_translations():

    """Copy the translation YAML files shipped in the ip-intelligence-data
    submodule into the package so they are included in the built distribution.
    This mirrors how the .NET project embeds the same files as resources. If the
    submodule is not present the package falls back to reading it at run time,
    so any failure here is ignored."""

    here = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(here, "..", "ip-intelligence-data", "Translations")
    dest = os.path.join(
        here, "src", "fiftyone_ipintelligence_translation", "translations")
    if not os.path.isdir(source):
        return
    os.makedirs(dest, exist_ok=True)

    def copy_yaml(folder):
        for name in os.listdir(folder):
            full = os.path.join(folder, name)
            if os.path.isfile(full) and name.endswith((".yml", ".yaml")):
                shutil.copyfile(full, os.path.join(dest, name))

    copy_yaml(source)
    osm = os.path.join(source, "OSM")
    if os.path.isdir(osm):
        copy_yaml(osm)


try:
    stage_translations()
except Exception:
    pass


setuptools.setup(
    name="fiftyone_ipintelligence_translation",
    version=read("version.txt"),
    author="51Degrees Engineering",
    author_email="engineering@51degrees.com",
    project_urls={
        "Homepage": "https://51degrees.com/ip-intelligence?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_translation&utm_term=homepage",
        "Documentation": "https://51degrees.com/documentation/_ip_intelligence__index.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_translation&utm_term=documentation",
        "Source": "https://github.com/51Degrees/51degrees-python",
    },
    description=("Country translation engines for 51Degrees on-premise IP Intelligence. Turns the weighted ISO country codes returned by the IP Intelligence engine into localized country names and complete ordered country lists."),
    long_description=read("readme.md"),
    long_description_content_type='text/markdown',
    python_requires=">=3.10",
    packages=["fiftyone_ipintelligence_translation"],
    package_dir={"": "src"},
    package_data={
        "fiftyone_ipintelligence_translation": ["translations/*.yml"]
    },
    install_requires=[
        "fiftyone_pipeline_core",
        "fiftyone_pipeline_translation",
        "PyYAML"
    ],
    license="EUPL-1.2",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "License :: OSI Approved :: European Union Public Licence 1.2 (EUPL 1.2)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],
    include_package_data=True
)
