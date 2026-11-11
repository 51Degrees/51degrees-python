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

from __future__ import absolute_import
import multiprocessing
import os.path

from .constants import *

from fiftyone_pipeline_engines.engine import Engine

from fiftyone_pipeline_core.basiclist_evidence_keyfilter import BasicListEvidenceKeyFilter

from .IpIntelligenceEngineModule import *

from .client_ip import client_ips
from .swig_data import SwigData
from .ipintelligence_datafile import IpIntelligenceDataFile


class IpIntelligenceOnPremise(Engine):
    """!
    The IP Intelligence On Premise engine uses a datafile to
    generate a list of properties about an IP address based on
    evidence supplied to it
    """

    def __init__(
        self,
        data_file_path=None,
        data=None,
        auto_update=None,
        cache=None,
        restricted_properties=None,
        licence_keys=None,
        download=True,
        file_system_watcher=False,
        polling_interval=30,
        update_time_maximum_randomisation=10,
        create_temp_data_copy=True,
        performance_profile="Balanced",
        reuse_temp_file=False,
        concurrency=multiprocessing.cpu_count(),
        update_on_start=False,
        data_update_url="https://distributor.51degrees.com/api/v2/download",
        data_update_use_url_formatter=True,
        data_update_verify_md5=True,
        data_update_product_type=None,
        **kwargs
    ):
        """!

        Constructor for the IP Intelligence On Premise Engine.

        @type data_file_path: string
        @param data_file_path: path to the data file (.ipi)
        @type data: binary
        @param data: in memory version of datafile
        @type auto_update: bool
        @param auto_update: whether to automatically update the datafile when required
        @type restricted_properties: list
        @param restricted_properties: List of property keys to limit the engine to
        @type licence_keys: string
        @param licence_keys: licencekeys to use for the data file update service
        @type download: bool
        @param download: whether to download the datafile or keep it in memory when it is returned from the datafile update service
        @type performance_profile: string
        @param performance_profile: options are: LowMemory, MaxPerformance,
        Balanced, BalancedTemp, HighPerformance. Balanced by default, as in
        the native code.
        @type reuse_temp_file: bool
        @param reuse_temp_file: Indicates that an existing temp file may be used. This should be selected if multiple instances wish to use the same file to prevent high disk usage.
        @type concurrency: int
        @param concurrency: defaults to the number of cpus in the machine
        @type update_on_start : bool
        @param update_on_start : When this is set to true the datafile is updated / downloaded immediately on initialization. This is useful if no initial datafile is present.
        @type file_system_watcher: bool
        @param file_system_watcher: whether to check the datafile's path for changes and update the connected FlowElement's data
        @type polling_interval: int
        @param polling_interval: How often to poll for updates to the datafile (minutes)
        @type update_time_maximum_randomisation : int
        @param update_time_maximum_randomisation :
        Maximum randomisation offset in seconds to polling time interval
        @type data_update_verify_md5 : bool
        @type create_temp_data_copy: bool
        @param create_temp_data_copy: whether to copy datafile to temporary location when updating
        @type data_update_url: string
        @param data_update_url: base url for the datafile update service
        @param data_update_use_url_formatter: This must be set to false to prevent the API from appending the query string parameters that are required when calling the 51Degrees Distributor service.
        @type data_update_use_url_formatter: bool

        """

        super(IpIntelligenceOnPremise, self).__init__()

        if cache is not None:
            raise Exception(CACHE_NOT_SUPPORTED)

        self.datakey = "ip"

        if not data_file_path and not data:
            raise Exception("data_file_path or data is required")

        if data_file_path:
            if os.path.isfile(data_file_path) == False and not update_on_start:
                raise Exception("There is no file at " + data_file_path)

            extention = os.path.splitext(data_file_path)[1]

            if extention != ".ipi":
                raise Exception("Data file name must end in .ipi")
        else:
            self.data = data

        if not licence_keys and licence_keys != "":
            raise Exception("licence key is required. A key can be obtained from the 51Degrees website: https://51degrees.com/pricing?utm_source=code&utm_medium=comment&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_onpremise-src-fiftyone_ipintelligence_onpremise-ipintelligence_onpremise.py&utm_term=licence-key-required. If you do not wish to use a key then you can specify an empty string, but this will cause automatic updates to be disabled.")

        #   Create SWIG wrapper vector for restricted properties and add

        restricted_properties_vector = VectorStringSwig()

        if restricted_properties:
            for restricted_property in restricted_properties:
                restricted_properties_vector.append(restricted_property)
            # Add the metric properties to the restricted properties as they
            # are always available
            for metric_property_name in self.get_metric_properties():
                restricted_properties.append(metric_property_name)
            self.set_restricted_properties(restricted_properties)

        properties_list = RequiredPropertiesConfigSwig(restricted_properties_vector)

        #  Assemble configuration

        config = ConfigIpiSwig()

        available_performance = ["LowMemory", "MaxPerformance", "Balanced", "BalancedTemp", "HighPerformance"]

        if performance_profile not in available_performance:
            raise Exception("Not a valid performance profile")

        if performance_profile == "LowMemory":
            config.setLowMemory()
        if performance_profile == "MaxPerformance":
            config.setMaxPerformance()
        if performance_profile == "Balanced":
            config.setBalanced()
        if performance_profile == "BalancedTemp":
            config.setBalancedTemp()
        if performance_profile == "HighPerformance":
            config.setHighPerformance()

        # Don't set an http_ prefix on evidence keys

        config.setUseUpperPrefixHeaders(False)

        # If auto update is enabled then we must use a temporary copy of the file

        if auto_update == True:
            config.setUseTempFile(True)

        if create_temp_data_copy == True:
            config.setUseTempFile(True)

        config.setReuseTempFile(reuse_temp_file)

        config.setConcurrency(concurrency)

        # Make engine

        self.config = config
        self.properties_list = properties_list
        self.data_file_path = data_file_path

        # Disable features that require a licence key if one was not supplied.

        if licence_keys:
            auto_update = auto_update and (len(licence_keys) > 0)
            update_on_start = update_on_start and (len(licence_keys) > 0)
        else:
            auto_update = False
            update_on_start = False

        if auto_update or update_on_start or file_system_watcher:

            # Construct DataFile

            update_url_params = {
                "base_url": data_update_url
            }

            if data_update_use_url_formatter:
                update_url_params = {
                    "base_url": data_update_url,
                    "type": "IPIV41",
                    "product": data_update_product_type if data_update_product_type else None,
                    "license_keys": licence_keys if licence_keys else None
                }

                # Remove keys with None values
                update_url_params = {k: v for k, v in update_url_params.items() if v is not None}

            data_file = IpIntelligenceDataFile(flow_element=self, identifier="IPIV41", verify_md5=data_update_verify_md5, auto_update = auto_update, update_on_start = update_on_start, decompress= True, path = data_file_path, download=download, file_system_watcher=file_system_watcher, polling_interval=polling_interval, update_time_maximum_randomisation=update_time_maximum_randomisation, update_url_params = update_url_params, data_update_use_url_formatter = data_update_use_url_formatter)

            self.register_data_file(data_file)

    def init_engine(self):

        """!

        Function for initialising the engine, wrapped like this so that an engine can be initialised once the datafile is retrieved if update_on_start is set to true. If this is the case, processing is held until the data file is downloaded and available.

        """

        if(self.data_file_path):
            data = self.data_file_path
        else:
            data = self.data

        engine = EngineIpiSwig(data, self.config, self.properties_list)

        self.engine = engine

        # Get keys and add to evidenceKey filter

        evidence_keys = engine.getKeys()

        evidence_keys_list = []

        for x in range(evidence_keys.size()):
            evidence_keys_list.append(evidence_keys.__getitem__(x).lower())

        self.evidence_keys_list = evidence_keys_list

        # Get properties list

        properties_internal = engine.getMetaData().getProperties()

        properties = {}

        for x in range(properties_internal.getSize()):
            current_property = properties_internal.getByIndex(x)
            if current_property.getAvailable():
                properties[current_property.getName().lower()] = {
                "name": current_property.getName(),
                "type": current_property.getType(),
                "datafiles": list(current_property.getDataFilesWherePresent()),
                "category": current_property.getCategory(),
                "description": current_property.getDescription(),
                "component": self.get_component(current_property)
            }

        self.properties = properties

        # Special properties
        for metric_property_name, metric_property in self.get_metric_properties().items():
            self.properties[metric_property_name] = metric_property

    def get_metric_properties(self):

        """!
        The synthetic properties added by this engine. The IP address
        supplied as evidence is echoed back in the results (dotnet parity).
        """

        return { "ip": {
          "name": 'Ip',
          "type": 'string',
          "category": 'IP Metrics',
          "description": IP_DESCRIPTION,
          "component": "IP Metrics"
        },
        "ipv6": {
          "name": 'IpV6',
          "type": 'string',
          "category": 'IP Metrics',
          "description": IPV6_DESCRIPTION,
          "component": "IP Metrics"
        }}

    def get_evidence_key_filter(self):
        """!
        Returns evidence key filter for the on premise engine.
        Generated via a list of evidence keys from the swig engine

        """

        return BasicListEvidenceKeyFilter(self.evidence_keys_list)


    def set_cache(self, cache):

        """!
        Not supported. Results read from native memory, which is not
        safe to share between requests through a cache.
        """

        raise Exception(CACHE_NOT_SUPPORTED)

    def on_registration(self, pipeline):

        """!

        Function called after the engine is registered with a pipeline
        the engine base class registers the datafile but we also need
        to initialise the SWIG wrapper so call self.init_engine() here
        after the datafile is registered.

        """

        super(IpIntelligenceOnPremise, self).on_registration(pipeline)
        self.init_engine()

    def close(self):

        """!

        Stop the data file updates and release the native engine. Its data
        is freed once no results read from it are still held, so close
        every FlowData the engine processed as well. Closing the pipeline
        closes the engine.

        """

        super(IpIntelligenceOnPremise, self).close()
        self.engine = None

    def get_client_ips(self, flow_data):

        """!

        Get the IPv4 and IPv6 addresses from every evidence key and value
        the flow data holds, as client_ips reads them.

        @rtype: tuple
        @returns: (ipv4 or None, ipv6 or None)

        """

        return client_ips(flow_data.evidence.get_all())

    def process_internal(self, flow_data):

        """!

        Internal process method of the IP Intelligence On Premise engine
        Gets properties through the SWIG wrapper and stores them in a
        SwigData extension of the ElementData class. Each property value
        (or lack of) is returned in an AspectPropertyValue wrapper from
        the core Pipeline library. Weighted properties are returned as
        lists of {"value": ..., "weighting": ...} dictionaries.

        """

        if getattr(self, "engine", None) is None:
            raise Exception(ENGINE_CLOSED)

        evidence = EvidenceIpiSwig()

        for key, value in flow_data.evidence.get_all().items():
            evidence.__setitem__(key, value)

        result = self.engine.process(evidence)

        ipv4, ipv6 = self.get_client_ips(flow_data)

        data = SwigData(self, result, echo_ip=ipv4, echo_ipv6=ipv6)

        flow_data.set_element_data(data)

    def get_component(self, property_metadata):
        return self.engine.getMetaData().getComponentForProperty(property_metadata).getName()
