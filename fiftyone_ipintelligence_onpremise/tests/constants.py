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


class TestConstants:

    IPV4_ADDRESS = "185.28.167.78"
    IPV6_ADDRESS = "2001:4860:4860::8888"

    # The data file can be supplied via the IPINTELLIGENCEDATAFILE
    # environment variable. By default the Lite file downloaded to the
    # repository's assets folder by ci/fetch-assets.ps1 is used.
    @staticmethod
    def get_data_file_path():
        env = os.environ.get("IPINTELLIGENCEDATAFILE")
        if env:
            return env
        return os.path.join(
            os.path.dirname(__file__),
            "..", "..", "assets", "51Degrees-LiteIpiV41.ipi")
