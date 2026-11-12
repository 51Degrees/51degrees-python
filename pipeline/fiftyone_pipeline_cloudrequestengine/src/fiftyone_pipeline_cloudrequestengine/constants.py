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
 
class Constants:
    # Environment variable to set cloud end point
    CLOUD_ENDPOINT = "_51DEGREES_CLOUD_ENDPOINT"

    # @deprecated Use Constants.CLOUD_ENDPOINT. This holds the old name of
    # the cloud end point environment variable, which the engine reads
    # through this constant when CLOUD_ENDPOINT is not set, so code that
    # passes this constant to the environment reads and sets the old
    # variable.
    FOD_CLOUD_API_URL = "FOD_CLOUD_API_URL"

    # Message when the cloud end point came from the old environment
    # variable. The first value is the old name and the second the new one.
    MESSAGE_OLD_ENDPOINT_VARIABLE = (
        "The {0} environment variable is deprecated and {1} replaces it. "
        "The cloud endpoint was read from {0} because {1} is not set, so "
        "set {1} to the same value.")

    # Default cloud end point
    BASE_URL_DEFAULT = "https://cloud.51degrees.com/api/v4/"
	
    # No Data in response message to be set in exception when cloud neither
    # return any data nor any error messages
    MESSAGE_NO_DATA_IN_RESPONSE = "No data in response from cloud service at {}"
	
    # Message when multiple errors are returned from cloud service
    EXCEPTION_CLOUD_ERRORS_MULTIPLE = \
            "Multiple errors returned from 51Degrees cloud service. See inner " + \
            "exceptions for details."

    # Message when single error is returned from cloud service
    EXCEPTION_CLOUD_ERROR = \
            "Error returned from 51Degrees cloud service: '{}'"

    # Evidence key seperator
    EVIDENCE_SEPERATOR = "."

    # Used to prefix evidence that is obtained from HTTP headers 
    EVIDENCE_HTTPHEADER_PREFIX = "header"

    # Used to prefix evidence that is obtained from HTTP bookies 
    EVIDENCE_COOKIE_PREFIX = "cookie"

    # Used to prefix evidence that is obtained from an HTTP request's
    # query string or is passed into the pipeline for off-line 
    # processing.
    EVIDENCE_QUERY_PREFIX = "query"

    # The prefixes after query, header and cookie, highest precedence
    # first, as evidence.md lists them. Any other prefix ranks after these,
    # alphabetically.
    OTHER_PREFIX_PRECEDENCE = ("server", "fiftyone", "location")

    # other evidence constant
    EVIDENCE_OTHER = "other"
    
    # warning message to be shown for conflicted evidences
    WARNING_MESSAGE = "WARNING: '{}:{}' evidence conflicts with "
    
    # error message when non-success status is returned.
    MESSAGE_ERROR_CODE_RETURNED = "Cloud service at '{}' returned status code '{}' with content {}"

    # The keys the cloud service reads its credentials and the list of
    # requested properties from, in the query string of a GET and in the
    # form body of a POST. See the Credentials section of the cloud request
    # engine specification:
    # https://github.com/51Degrees/specifications/blob/main/pipeline-specification/pipeline-elements/cloud-request-engine.md#credentials
    RESOURCE_PARAMETER = "resource"
    LICENSE_PARAMETER = "license"
    VALUES_PARAMETER = "values"

    # The cloud service reads these names among its accepted evidence
    # keys, so evidence such as "query.license" would otherwise go into the
    # request body beside the engine's own credentials, with no way to say
    # which one the service applied. Evidence whose key strips to one of
    # them is left out of every request.
    LICENCE_SPELLING = "licence"
    RESERVED_EVIDENCE_SUFFIXES = (
        RESOURCE_PARAMETER, LICENSE_PARAMETER, LICENCE_SPELLING,
        VALUES_PARAMETER)

    # The path, below the base URL, of the data endpoint that takes no
    # resource key in its route, used when the engine authenticates on a
    # licence key alone.
    LICENSE_DATA_PATH = "json"

    # Logged when evidence is left out of a request because its key is one
    # the service reads its credentials or requested properties from. The
    # value is not included, as it may be a credential.
    WARNING_RESERVED_EVIDENCE = (
        "WARNING: '{}' evidence is not sent to the cloud service, because "
        "the service reads its credentials and the list of requested "
        "properties from that name. The engine's own settings are sent "
        "instead.")

    # Messages for the credential combinations the engine refuses when it is
    # built. Each says why the combination cannot work, because the rule on
    # its own reads as arbitrary.
    MESSAGE_NO_CREDENTIAL = (
        "CloudRequestEngine needs a resource key or a licence key to "
        "authenticate with, as the cloud service answers 401 to a request "
        "that carries neither. Create a resource key for free at "
        "https://configure.51degrees.com?utm_source=code&utm_medium=comment&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_cloudrequestengine-src-fiftyone_pipeline_cloudrequestengine-constants.py&utm_term=no-credential")
    MESSAGE_LICENSE_KEY_NEEDS_PROPERTIES = (
        "CloudRequestEngine has a licence key and no requested_properties. "
        "A licence key names no properties of its own, so the cloud service "
        "answers 400 to every request made with one that does not list the "
        "properties it wants. Set requested_properties to the fully "
        "qualified names wanted, for example "
        "['device.ismobile', 'device.iscrawler'].")

    # Logged once when a request with a licence key named properties and
    # the response left some of them out without saying so. Both the
    # licence behind a resource key and a licence key beside it decide
    # what comes back, so the message names the keys rather than one key.
    MESSAGE_PROPERTIES_NOT_COVERED = (
        "The cloud service did not return the requested properties {} in "
        "its answer. They are not covered by the keys in use, so they "
        "will be missing from every result. The other requested "
        "properties came back and are usable.")
    # Logged once when a request with a resource key and no licence key
    # named properties and the response left some of them out. Without a
    # licence key a property no licence grants comes back as null with a
    # reason, so a name left out is not a property.
    MESSAGE_PROPERTIES_NOT_KNOWN = (
        "The cloud service did not return the requested properties {} in "
        "its answer. Every property is answered, with a reason when it has "
        "no value, so these names are not properties. Check the spelling "
        "of each one. The other requested properties came back and are "
        "usable.")
