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

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import \
    BasicListEvidenceKeyFilter
from fiftyone_pipeline_engines.engine import Engine
from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue
from fiftyone_pipeline_core.jsonbundler import WKT_TYPES

from .clouddata import CloudData

import json
import threading

from fiftyone_pipeline_engines.missingproperty_service import MissingPropertyService

class OnPremiseMissingPropertyService(MissingPropertyService):

    def check(self, key, flow_element):

        raise Exception('Property ' + key + ' not found in data for element ' + flow_element.datakey + '. Please check that the element and property names are correct.')

class CloudEngine(Engine):

    """!
    This is a template for all 51Degrees cloud engines.
    It requires the 51Degrees cloudRequestEngine to be placed in a
    pipeline before it. It takes that raw JSON response and
    parses it to extract the device part.
    It also uses this data to generate a list of properties.

    """

    def __init__(self):

        super(CloudEngine, self).__init__()

        self.datakey = "CloudEngineBase" # This should be overriden

        # The cloud request engine the property metadata comes from, set
        # when this engine is added to a pipeline, and whether the metadata
        # is final. It is not final until that engine's discovery has
        # completed, so an empty answer from before then is not kept.
        self._request_engine = None
        self._properties_final = False
        self._properties_lock = threading.Lock()

    def get_evidence_key_filter(self):

        """!
        A cloud engine reads only the cloud request engine's results, so it
        accepts no evidence.
        """

        return BasicListEvidenceKeyFilter([])

    def on_registration(self, pipeline):
 
        """!
        Callback called when an engine is added to a pipeline
        In this case sets up the properties list for the element from
        data in the CloudRequestEngine

        If the CloudRequestEngine could not fetch the accessible properties
        when it was built, the pipeline is still built and this engine has
        no properties until that engine fetches them on first use.

        @type pipeline: Pipeline
        @param pipeline

        """

        if not "cloud" in pipeline.flow_elements_list:
            raise Exception("CloudRequestEngine needs to be placed before cloud elements in Pipeline")

        with self._properties_lock:
            self._request_engine = pipeline.flow_elements_list["cloud"]
            self._properties_final = False
            self.properties = {}
        self._load_properties(pipeline.log)

        # Add a special message to the pipeline
        # when requesting an element that does not exist

        pipeline.element_not_found = self.pipeline_element_not_found

    def get_properties(self):

        """!
        The properties of this engine, taken from the CloudRequestEngine.
        They are empty until that engine's discovery has completed.

        @rtype: dict
        @return: Returns the properties keyed by lower-case name
        """

        self._load_properties(self._log)
        return super(CloudEngine, self).get_properties()

    def _load_properties(self, log):

        """!
        Take this engine's properties from the CloudRequestEngine once its
        discovery has completed, and keep them from then on. Until then
        the properties stay empty and are looked for again on the next
        use, as the Cloud Aspect Engine specification asks.

        @type log: callable
        @param log: takes a level and a message, as Pipeline.log does
        """

        if self._properties_final or self._request_engine is None:
            return

        with self._properties_lock:
            if self._properties_final:
                return
            carried = self._known_properties()
            if carried is None:
                return
            self._properties_final = True

            # The accessible properties come from the cloud service for
            # the key in use, a resource key or a licence key, so a section
            # missing from them means that key does not carry the product
            # at all. That is not a configuration error, so the engine has
            # no properties and the missing product is logged here, once.
            if not self.datakey in carried:
                log("warning", "The key in use does not include access to any properties under the engine with key " + self.datakey +  " that was added to the pipeline. For more details on resource keys, see our explainer: https://51degrees.com/documentation/_services__cloud__resource_keys.html?utm_source=code&utm_medium=comment&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine-src-fiftyone_pipeline_cloudrequestengine-cloudengine.py&utm_term=engine-properties-not-accessible " + "Available engine data keys are: " + str([e for e in carried]))
                self.properties = {}
            else:
                self.properties = carried[self.datakey]

    def _known_properties(self):

        """!
        The CloudRequestEngine's accessible properties, or None while its
        discovery has not completed. No request is made.
        """

        engine = self._request_engine
        known = getattr(engine, "known_flow_element_properties", None)
        if known is None:
            # An element that stands in for the CloudRequestEngine, such
            # as one in a test, gives its properties directly.
            return engine.flow_element_properties
        return known()

    def pipeline_element_not_found(self, element, flowdata):
        """!
        Custom error when an element cannot be found in the pipeline

        @type element: string
        @param element: name of flowelement 
        @type flowdata: flowdata
        @param element: flowdata being processsed 
        @rtype: Exception
        @return: Returns exception

        """

        raise Exception("The key in use does not include access to any properties under " + element +  ". For more details on resource keys, see our explainer: https://51degrees.com/documentation/_services__cloud__resource_keys.html?utm_source=code&utm_medium=comment&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine-src-fiftyone_pipeline_cloudrequestengine-cloudengine.py&utm_term=element-properties-not-accessible " + "Available element data keys are: " + str([e for e in flowdata.pipeline.flow_elements_display_list]))


    def process_internal(self, flowdata):

        """!
        Process function of a cloud engine.
        This organises and parses data returned from the Cloud Request Engine
        and adds it to the FlowData

        @type flowdata: FlowData
        @param flowdata: FlowData to process

        """

        # The CloudRequestEngine has processed first, so its discovery may
        # have completed since this engine last looked.
        self._load_properties(self._log)

        cloud_data = flowdata.get("cloud").get("cloud")

        cloud_data = json.loads(cloud_data)

        # A request made with a licence key only carries the sections it
        # asked for, so a section the key carries can still be absent from
        # one answer. Treat that as no values rather than failing the
        # request, so the other sections stay usable.
        engineData = cloud_data.get(self.datakey, {})

        result = {}

        # A shape in well-known text arrives as an object holding the text.
        # The property list is keyed by the names the cloud service gives,
        # such as Areas, and the response by the same names in lower case.
        wkt_keys = {
            name.lower() for name, meta in self.properties.items()
            if str(meta.get("type", "")).lower() in WKT_TYPES}

        for key, value in engineData.items():

            if (key.lower() in wkt_keys and isinstance(value, dict)
                    and list(value) == ["value"]):
                value = value["value"]

            if key + "nullreason" in engineData:
                result[key] = AspectPropertyValue(no_value_message=engineData[key + "nullreason"])
            else:
                result[key] = AspectPropertyValue(None, value)

        data = CloudData(self, result)
            
        flowdata.set_element_data(data)
