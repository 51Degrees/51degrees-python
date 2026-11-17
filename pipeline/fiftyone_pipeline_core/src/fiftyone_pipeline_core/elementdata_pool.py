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
import threading

# The most instances a pool keeps, twice the number of processors. An
# instance given back to a full pool is left to the garbage collector.
DEFAULT_MAXIMUM_INSTANCES = 2 * (os.cpu_count() or 1)


class ElementDataPool(object):

    """!
    A bounded pool of the ElementData one FlowElement makes, so that a
    request reuses an instance an earlier request has finished with rather
    than making a new one. The FlowElement keeps it as _element_data_pool
    and takes from it while it processes. FlowData.close() gives each
    instance back after closing it.

    An instance from the pool has no values and is open for writing, as
    take() calls its _clear method, which a class with values of its own
    overrides to drop them. An instance a cache may hold never goes back,
    because the cache shares it with other requests, and the instances of a
    FlowData that is not closed are left to the garbage collector.

    Requests on several threads share the pool, so it takes a lock of its
    own. It never locks a FlowData or ElementData.

    """

    def __init__(self, maximum_instances=DEFAULT_MAXIMUM_INSTANCES):

        """!
        @type maximum_instances: int
        @param maximum_instances: the most instances the pool keeps

        """

        self.maximum_instances = maximum_instances
        self._instances = []
        self._lock = threading.Lock()

    def take(self):

        """!
        An instance an earlier request has finished with, with no values and
        open for writing.

        @rtype: ElementData
        @return: the instance, or None when the pool has none, when the
        FlowElement makes a new one

        """

        with self._lock:
            if not self._instances:
                return None
            element_data = self._instances.pop()
        element_data._clear()
        return element_data

    def give_back(self, element_data):

        """!
        Keep an instance for a later request, unless the pool is full or the
        FlowElement that made it has a cache, which may hold it.

        @type element_data: ElementData
        @param element_data: an instance whose FlowData has been closed

        """

        if getattr(element_data.flow_element, "cache", None) is not None:
            return
        with self._lock:
            if len(self._instances) < self.maximum_instances:
                self._instances.append(element_data)

    def __len__(self):

        """!
        @rtype: int
        @return: the number of instances the pool holds

        """

        with self._lock:
            return len(self._instances)
