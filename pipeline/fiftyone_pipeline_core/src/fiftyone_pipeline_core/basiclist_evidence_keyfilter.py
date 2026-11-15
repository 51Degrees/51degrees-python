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

from .evidence_keyfilter import EvidenceKeyFilter


class BasicListEvidenceKeyFilter(EvidenceKeyFilter):

    """!
    An instance of EvidenceKeyFilter that uses a simple array of keys
    Evidence not using these keys is filtered out

    A key is looked up in a set made from list at the first lookup, and
    made again whenever list is set to another list. To change the keys
    once the filter has been used, set list to a new list rather than
    changing the list in place.

    """

    def __init__(self, keys_list):
        
        """!
        BasicListEvidenceKeyFilter constructor

        @type keysList: dict 
        @param keysList: a list of keys to keep.

        """

        # lowercase keys list
        self.list = [item.lower() for item in keys_list]

    def filter_evidence_key(self, key):

        """!
        Check if an evidence key is present in a filter list.

        @type key: string
        @param key: to check in the filter

        @rtype: bool
        @return: Is this key in the filter's keys list?

        """

        # The set is kept with the list it was made from, as one value, so
        # a lookup on another thread never finds a set beside a list it was
        # not made from. Reading list each time finds a list set after the
        # filter was made, or set by a subclass that does not call the
        # constructor.
        listed = self.list
        made = getattr(self, "_list_as_set", None)
        if made is None or made[0] is not listed:
            made = (listed, set(listed))
            self._list_as_set = made
        return key.lower() in made[1]
