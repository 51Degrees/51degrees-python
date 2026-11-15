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

import requests

from .constants import Constants


class RequestClient:

    """!
    Sends the cloud request engine's requests with the requests library.
    A request waits at most its timeout to connect, and at most that long
    again for each part of the answer, so a cloud service that takes the
    connection and never answers cannot hold the caller.
    """

    # The timeout of a subclass whose constructor does not call this one.
    timeout_seconds = Constants.TIMEOUT_SECONDS_DEFAULT

    def __init__(self, timeout_seconds=Constants.TIMEOUT_SECONDS_DEFAULT):

        """!
        @type timeout_seconds: number
        @param timeout_seconds: how long a request waits, in seconds, when
        it is not given a timeout of its own
        """

        self.timeout_seconds = timeout_seconds

    def request(self, type, url, content, originHeader, timeout_seconds=None):

        """!
        Send one request to the cloud service and give its response.

        @type timeout_seconds: number
        @param timeout_seconds: how long the request waits, in seconds, or
        None for the timeout the client was built with
        """

        if timeout_seconds is None:
            timeout_seconds = self.timeout_seconds
        return requests.request(
            type, url, data=content, headers={"Origin": originHeader},
            timeout=timeout_seconds)
