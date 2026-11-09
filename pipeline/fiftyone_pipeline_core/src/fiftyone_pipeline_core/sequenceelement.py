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


from .flowelement import FlowElement
from .evidence_keyfilter import EvidenceKeyFilter
from .javascriptbuilder import parse_sequence
from .elementdata_dictionary import ElementDataDictionary
import re
import uuid

# Text that is a sequence, in ASCII decimal digits and nothing else.
DIGITS_PATTERN = re.compile(r"[0-9]+")

class SequenceElementEvidenceKeyFilter(EvidenceKeyFilter):

    def filter(self, key):
    
        if (key == "query.sequence" or key == "query.session-id"):
            return True
            
        return False


class SequenceElement(FlowElement):

    """!
    The SequenceElement stores session data regarding
    requests for client side JavaScript from the JavaScript
    created by a Pipeline's JavaScriptBuilder
    If a Pipeline is constructed with the JavaScript elements
    enabled this is added automatically along with the JavaScriptBuilder
    and JSONBundler.
    """

    def __init__(self):

        super(SequenceElement, self).__init__()

        self.datakey = "sequence"
        self.properties = {
            "session-id": {"type": "string"},
            "sequence": {"type": "int"}}
        self.exclude_from_messages = True


    def get_evidence_key_filter(self):
    
        """!
        The SequenceElement uses query.sequence and query.session-id evidence
        """
  
        return SequenceElementEvidenceKeyFilter()

    def process_internal(self, flowdata):

        """!
        The SequenceElement stores session data for requests for JavaScript,
        in its Element Data (session-id and sequence) and in Evidence
    
        @type flowdata: FlowData
        @param flowdata: The FlowData

        """
    
        # The session id and the sequence are read independently. A session
        # id that is not a non-empty string is absent, and gets a new id. A
        # sequence that is not a whole number from 1 to 2147483647, written
        # in decimal digits if it is text, is absent and gives 1.
        session_id = flowdata.evidence.get("query.session-id")
        if not isinstance(session_id, str) or session_id == "":
            session_id = str(uuid.uuid4())

        sequence = flowdata.evidence.get("query.sequence")
        if isinstance(sequence, str) and not DIGITS_PATTERN.fullmatch(sequence):
            sequence = None
        sequence = parse_sequence(sequence)
        sequence = 1 if sequence is None else sequence + 1

        flowdata.evidence.add("query.session-id", session_id)
        flowdata.evidence.add("query.sequence", sequence)

        flowdata.set_element_data(ElementDataDictionary(
            self, {"session-id": session_id, "sequence": sequence}))
