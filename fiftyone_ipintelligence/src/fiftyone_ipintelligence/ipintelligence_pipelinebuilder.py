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

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import CloudRequestEngine
from fiftyone_ipintelligence_cloud.ipintelligence_cloud import IpIntelligenceCloud
from fiftyone_ipintelligence_onpremise.ipintelligence_onpremise import IpIntelligenceOnPremise
from fiftyone_ipintelligence_shared.utils import merge_two_dicts

from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage

class IpIntelligencePipelineBuilder(PipelineBuilder):
    """!
    The IP Intelligence Pipeline Builder allows you to easily
    construct a pipeline containing either the cloud or on-premise
    IP intelligence engine depending on the parameters supplied.
    """
    def __init__(self, settings = None, usage_sharing = True, **kwargs):

        """!

        Constructor for the IP Intelligence Pipeline Builder.
        Depending on parameters passed through, builds a pipeline
        with either the cloud or on premise IP intelligence engines

        General pipeline settings:

        @type javascript_builder_settings: dict
        @param javascript_builder_settings: parameters for the pipeline's JavaScript builder to populate additional evidence from the clientside.
            - obj_name: the name of the client side object
            with the JavaScript properties in it ('fod' by default)
            - protocol: The protocol ("http" or "https") used by
            the client side callback url. This can be overridden
            with header.protocol evidence
            - host The host of the client side callback url.
            This can be overridden with header.host evidence.
            - endpoint The endpoint of the client side callback url
            * enable_cookies - whether cookies should be enabled
            * minify: Whether to minify the JavaScript
        @type cache: Cache
        @param cache: An instance of the fiftyone.pipeline.engines.cache
        class

        Cloud Engine Settings:

        @type resource_key: string
        @param resource_key: the 51Degrees cloud resource key
        @type cloud_request_origin: string
        @param cloud_request_origin: the value to use for the Origin header when making requests to the cloud service

        On Premise Engine Settings:

        @type usage_sharing : bool
        @param usage_sharing : Whether to enable usage sharing if using the on premise engine
        @type data_file_path: string
        @param data_file_path: path to the data file (.ipi)
        @type auto_update: bool
        @param auto_update: whether to automatically update the datafile when required
        @type restricted_properties: list
        @param restricted_properties: List of property keys to limit the engine to
        @type licence_keys: string
        @param licence_keys: licencekeys to use for the data file update service
        @type download: bool
        @param download: whether to download the datafile or keep it in memory when it is returned from the datafile update service
        @type performance_profile: string
        @param performance_profile: options are: LowMemory, MaxPerformance, Balanced, BalancedTemp, HighPerformance
        @type reuse_temp_file: bool
        @param reuse_temp_file: Indicates that an existing temp file may be used. This should be selected if multiple instances wish to use the same file to prevent high disk usage.
        @type concurrency: int
        @param concurrency: defaults to the number of cpus in the machine
        @type update_on_start : bool
        @param update_on_start : When this is set to true the datafile is updated / downloaded immediately on initialisation. This is useful if no initial datafile is present.
        @type file_system_watcher: bool
        @param file_system_watcher: whether to check the datafile's path for changes and update the connected FlowElement's data
        @type polling_interval: int
        @param polling_interval: How often to poll for updates to the datafile (minutes)
        @type update_time_maximum_randomisation : int
        @param update_time_maximum_randomisation :
        Maximum randomisation offset in seconds to polling time interval
        @type create_temp_data_copy: bool
        @param create_temp_data_copy: whether to copy datafile to temporary location when updating
        @type data_update_url: string
        @param data_update_url: base url for the datafile update service

        """
        if settings is None:
            settings = {}

        settings = merge_two_dicts(dict(**kwargs), locals())

        settings = merge_two_dicts(settings, settings["settings"])

        del settings["self"]

        super(IpIntelligencePipelineBuilder, self).__init__(settings)

        # Add specific engines

        if "data_file_path" in settings:
            del settings["settings"]
            ip_engine = IpIntelligenceOnPremise(**settings)

            # If usage sharing enabled, add usage sharing engine

            if usage_sharing:
                self.add(ShareUsage())

        else :
            self.add(CloudRequestEngine(settings))
            ip_engine = IpIntelligenceCloud()

        if "cache" in settings:
            ip_engine.set_cache(settings["cache"])

        self.add(ip_engine)
