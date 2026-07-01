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

import os

import yaml

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_PACKAGED_TRANSLATIONS = os.path.join(_PACKAGE_DIR, "translations")


def _find_submodule_translations():

    """Walk up from this package looking for the ip-intelligence-data
    submodule's Translations directory, used when the package is run from a
    source checkout rather than an installed distribution."""

    current = _PACKAGE_DIR
    for _ in range(8):
        candidate = os.path.join(
            current, "ip-intelligence-data", "Translations")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def _translation_files():

    """Return a dict of translation file name -> absolute path. The packaged
    translations directory is preferred; if it is empty the ip-intelligence-data
    submodule is used as a fallback (countrycodes at the root, countries under
    OSM)."""

    files = {}

    if os.path.isdir(_PACKAGED_TRANSLATIONS):
        for name in os.listdir(_PACKAGED_TRANSLATIONS):
            if name.endswith((".yml", ".yaml")):
                files[name] = os.path.join(_PACKAGED_TRANSLATIONS, name)
    if files:
        return files

    base = _find_submodule_translations()
    if base is not None:
        for name in os.listdir(base):
            if name.endswith((".yml", ".yaml")):
                files[name] = os.path.join(base, name)
        osm = os.path.join(base, "OSM")
        if os.path.isdir(osm):
            for name in os.listdir(osm):
                if name.endswith((".yml", ".yaml")):
                    files[name] = os.path.join(osm, name)
    return files


def _read(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def get_country_code_resources():

    """!
    Get the country code translation YAML files (countrycodes.*), keyed on file
    name. This is the code-to-English-name stage and the list of all known
    countries.
    """

    return {
        name: _read(path)
        for name, path in _translation_files().items()
        if name.lower().startswith("countrycodes")
    }


def get_country_resources():

    """!
    Get the country name translation YAML files (countries.*), keyed on file
    name. These map English name to localized name, one file per locale.
    """

    return {
        name: _read(path)
        for name, path in _translation_files().items()
        if name.lower().startswith("countries")
    }


def get_all_countries():

    """!
    Load the country code resource into an ordered list of (code, English name)
    pairs, as they appear in countrycodes.en_GB.yml. This is the complete set of
    known countries.
    """

    resources = get_country_code_resources()
    if not resources:
        return []
    content = next(iter(resources.values()))
    data = yaml.safe_load(content) or {}
    return [(str(code), str(name)) for code, name in data.items()]
