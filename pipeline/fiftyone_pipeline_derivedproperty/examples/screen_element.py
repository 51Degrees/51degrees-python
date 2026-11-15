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

"""!
The flow element that gives the properties the derived property example's
scripts read. It is in a module of its own so that the example's
configuration file can name it, as it names any other element.
"""

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.elementdata_dictionary import \
    ElementDataDictionary
from fiftyone_pipeline_core.flowelement import FlowElement

# The evidence the element reads, the width and height of the screen in
# pixels, as a web page could send them in its query string.
SCREEN_WIDTH = "query.screenwidth"
SCREEN_HEIGHT = "query.screenheight"


class ScreenElement(FlowElement):

    """!
    Gives the width and height of a screen in pixels, as the properties
    Width and Height under the element data key screen, so a script names
    them screen.Width and screen.Height. A property is given only when the
    request carries its evidence as a whole number.
    """

    def __init__(self):

        super(ScreenElement, self).__init__()

        self.datakey = "screen"

        # The derived property element refuses a pipeline in which no
        # element lists a property its scripts read, so these are the names
        # the scripts use after the dot.
        self.properties = {
            "width": {
                "name": "Width",
                "type": "int",
                "description": "The width of the screen in pixels."
            },
            "height": {
                "name": "Height",
                "type": "int",
                "description": "The height of the screen in pixels."
            }
        }

    def get_evidence_key_filter(self):

        """!
        The evidence the element reads. The pipeline sets aside any evidence
        that no flow element reads.
        """

        return BasicListEvidenceKeyFilter([SCREEN_WIDTH, SCREEN_HEIGHT])

    def process_internal(self, flowdata):

        """!
        Adds each property whose evidence the request carries. A property
        left out has no value on this request.
        """

        result = {}
        for name, key in (("Width", SCREEN_WIDTH), ("Height", SCREEN_HEIGHT)):
            value = flowdata.evidence.get(key)
            if value is not None and str(value).strip().isdecimal():
                result[name] = int(value)

        flowdata.set_element_data(ElementDataDictionary(self, result))
