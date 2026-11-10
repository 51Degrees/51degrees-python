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

# The key the web integration gives the web request itself, which the usage
# sharing element reads. No element uses it as evidence, so filter() always
# sets it aside, whatever the elements' filters accept.
HTTP_REQUEST_KEY = "server.http-request"


class Evidence:
    def __init__(self, flowdata):
        """!
        Constructor for Evidence container on a FlowData

        @type flowdata: FlowData
        @param flowdata: Parent FlowData
        """
        self.evidence = {}
        self.evidence_filtered = False
        self.flowdata = flowdata
        self.unaccepted = {}

    def add(self, key, value):
        """!
        Add a single piece of evidence by its element and value

        @type key: string
        @param key: a flowElement's datakey

        @type value: mixed
        @param value: a piece of evidence
        """

        self.evidence[key] = value

    def add_from_dict(self, evidence_dictionary):
        """!
        Helper function to set multiple pieces of evidence from a dict

        @type evidence_dictionary: dict
        @param evidence_dictionary: Dict of evidence
        """

        if not type(evidence_dictionary) is dict:
            self.flowdata.set_error("core", "Must pass valid dictionary.")

        for key, value in evidence_dictionary.items():
            self.add(key, value)

    def get(self, key):
        """!
        Get a piece of evidence by key

        @type key: string
        @param key: A FlowElement's datakey

        @rtype: dict
        @return: A piece of evidence
        """

        if key in self.evidence:

            return self.evidence[key]

        else:

            return

    def get_all(self):
        """!
        Get all evidence

        @rtype: dict
        @return: Returns everything in this Evidence.evidence
        """

        return self.evidence

    def get_unaccepted(self):
        """!
        The evidence filter() set aside, being the keys no FlowElement in
        the pipeline accepts and the web request itself. The usage sharing
        element accepts no evidence, and shares what it finds here and in
        get_all().

        @rtype: dict
        @return: The evidence set aside, empty until filter() runs
        """

        return self.unaccepted

    def filter(self) -> None:
        """!
        Filter evidence using `filter_evidence_key` and
        `filter_evidence` methods of each FlowElement in the pipeline. The
        keys that do not pass, and the web request under HTTP_REQUEST_KEY,
        move to get_unaccepted().
        """

        if self.evidence_filtered:
            return

        # Loop over a copy of the keys, as keys are removed on the way.
        for key in list(self.evidence):
            if str(key).lower() == HTTP_REQUEST_KEY or not any([
                flow_element.filter_evidence_key(key)
                for flow_element
                in self.flowdata.pipeline.flow_elements
            ]):
                self.unaccepted[key] = self.evidence.pop(key)

        self.evidence_filtered = True
