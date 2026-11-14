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
The examples download a free data file that is missing, by running the data
repository's script for it. CI puts the free files in place before the tests
run, so nothing else there makes an example download one.

This test makes a folder that holds only what a fresh clone holds before
anything is downloaded, being the data repository's download scripts and its
link to the free Asn file, which is the smallest free IP Intelligence file.
It then looks for the Asn file from that folder, as an example does, and the
file must be downloaded and open as a free data file.
"""

import os
import shutil
from pathlib import Path

from fiftyone_ipintelligence_examples.example_utils import ExampleUtils
from fiftyone_ipintelligence_shared.example_constants import \
    ASN_DATAFILE_NAME

# The data repository in this checkout, which holds the download scripts
# and a link to each free file.
DATA = Path(__file__).resolve().parents[3] / "cxx" / "data"

# The scripts the download runs, the shell one on Linux and macOS and the
# PowerShell one on Windows.
SCRIPTS = ("get-data-files.sh", "get-data-files.ps1")

# The Asn file is about 6 MB, so anything under this is not the whole file.
ASN_MINIMUM_BYTES = 1024 * 1024


def test_find_file_downloads_a_missing_asn_file(tmp_path, monkeypatch, capfd):
    link = DATA / "ip-intelligence" / (ASN_DATAFILE_NAME + ".link")
    assert link.is_file(), (
        f"{link} is missing. Check out the submodules with "
        "git submodule update --init --recursive.")
    folder = tmp_path / ExampleUtils.DATA_FOLDER
    folder.mkdir(parents=True)
    for script in SCRIPTS:
        shutil.copy(DATA / script, folder.parent / script)
    shutil.copy(link, folder / link.name)
    # A data file named in the environment would be used in place of the
    # search.
    monkeypatch.delenv(ExampleUtils.IPI_PATH_ENV_VAR, raising=False)
    monkeypatch.delenv(ExampleUtils.DATA_FILE_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)

    found = ExampleUtils.find_file(ASN_DATAFILE_NAME)

    captured = capfd.readouterr()
    printed = captured.out + captured.err
    expected = folder / ASN_DATAFILE_NAME
    assert found is not None, printed
    assert os.path.samefile(found, expected), printed
    assert expected.stat().st_size > ASN_MINIMUM_BYTES, printed
    assert ExampleUtils.is_free_data_file_at(found), printed
