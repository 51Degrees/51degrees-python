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
from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_cloudrequestengine.cloudrequestengine import CloudRequestEngine
from .ipintelligence_cloud import IpIntelligenceCloud
from fiftyone_ipintelligence_shared.utils import merge_two_dicts

class IpIntelligenceCloudPipelineBuilder(PipelineBuilder):
    """!
    The IP Intelligence Cloud Pipeline Builder allows you to easily
    construct a pipeline containing the IP intelligence cloud engine.
    """
    def __init__(self, settings = None, **kwargs):

        """!

        Constructor for the IP Intelligence Cloud Pipeline Builder

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
        @type cloud_endpoint: string
        @param cloud_endpoint: the 51Degrees cloud service endpoint to use. Defaults to https://cloud.51degrees.com/api/v4/
        @type cloud_request_origin: string
        @param cloud_request_origin: The value to set the Origin header to when making requests to the cloud service

        """
        if settings is None:
            settings = {}

        settings = merge_two_dicts(dict(**kwargs), locals())

        settings = merge_two_dicts(settings, settings["settings"])

        del settings["self"]

        super(IpIntelligenceCloudPipelineBuilder, self).__init__(settings)

        # Add specific engines

        self.add(CloudRequestEngine(settings))
        ip_engine = IpIntelligenceCloud()

        if "cache" in settings:
            ip_engine.set_cache(settings["cache"])

        self.add(ip_engine)
