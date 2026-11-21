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

 # Messages which may be reused for various property exceptions.

class Messages():

    # Property does not start with SetHeader. This takes the name of a property
    # as a format argument.

    PROPERTY_NOT_SET_HEADER = "Property Name '{}' does not start with 'SetHeader'."

    # Property Name is not in the valid format. This takes the property name 
    # as format argument.

    WRONG_PROPERTY_FORMAT = \
        "Property Name '{}' is not in the expected format i.e. SetHeader[Identifier][HeaderName]. "
    
    # Element not found in flowData. This takes the element datakey 
    # as format argument.
    ELEMENT_NOT_FOUND = \
        "Element '{}' is not present in the FlowData. "

    # Property not found in flowData. This takes the element datakey
    # and property names as format arguments.
    PROPERTY_NOT_FOUND = \
        "Property '{}' is not present in the FlowData against '{}' ElementData. "

    # FlowData already processed.
    FLOW_DATA_PROCESSED = "FlowData already processed"

    # A write to a FlowData that has finished processing. This takes what was
    # being added as a format argument.
    FLOW_DATA_FINISHED = (
        "This FlowData has finished processing, so {} cannot be added to it. "
        "A FlowData is read only once processing has finished.")

    # A write to ElementData once its FlowElement has finished. This takes
    # the name written and the element's data key as format arguments.
    ELEMENT_DATA_FINISHED = (
        "'{}' cannot be written to the '{}' ElementData, because the "
        "FlowElement that writes it has finished processing. ElementData is "
        "written only while the FlowElement that provides it processes.")

    # The usage sharing element is not the last Flow Element. This takes the
    # element's class name, its position counting from 1 and the number of
    # Flow Elements as format arguments.
    USAGE_SHARING_NOT_LAST = (
        "The usage sharing element must be the last Flow Element and "
        "outside any parallel group. {} is Flow Element {} of {} in this "
        "Pipeline.")
