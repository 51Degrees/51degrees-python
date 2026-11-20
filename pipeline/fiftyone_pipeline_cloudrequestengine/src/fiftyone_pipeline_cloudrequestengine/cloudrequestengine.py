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

import inspect
import json
import math
import os
# Kept so that ``from ... import *`` of this module still gives it.
import threading
import warnings
from functools import cached_property
from json import JSONDecodeError

import requests
from fiftyone_pipeline_core.basiclist_evidence_keyfilter import BasicListEvidenceKeyFilter
from fiftyone_pipeline_core.evidence import HTTP_REQUEST_KEY
from fiftyone_pipeline_core.keymask import mask_licence_key
from fiftyone_pipeline_core.keymask import mask_licence_keys_in_text
from fiftyone_pipeline_engines.engine import Engine
from fiftyone_pipeline_engines.aspectdata_dictionary import AspectDataDictionary

from .requestclient import RequestClient
from .cloudrequestexception import CloudRequestException
from .constants import Constants

try:
    #python2
    from urllib import urlencode
except ImportError:
    #python3
    from urllib.parse import urlencode


def _endpoint_from_environment():

    """!
    The cloud end point that Constants.CLOUD_ENDPOINT names, or None when
    it is unset or empty.

    @rtype: string
    @return: the end point, or None
    """

    return os.environ.get(Constants.CLOUD_ENDPOINT) or None


def _takes_timeout(client):

    """!
    Whether a client's request method has a timeout_seconds parameter. A
    client written for an older RequestClient has none, so it is called
    without one.
    """

    try:
        parameter = inspect.signature(client.request).parameters.get(
            "timeout_seconds")
    except (TypeError, ValueError):
        return False
    return parameter is not None and parameter.kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY)


# Engine that makes a call to the 51Degrees cloud service. It gives the raw
# JSON as its "cloud" property, read under the "cloud-response" key, or
# under the deprecated key "cloud".
class CloudRequestEngine(Engine):
    def __init__(self, settings = {}):
        """!
        Constructor for CloudRequestEngine
        
        @type settings: dict
        @param settings: Settings should contain a resource_key or a
        license_key, and optionally
        1) requested_properties, the fully qualified names of the
        properties to ask for, as a list or a comma separated string.
        Required with a license_key alone. Beside a resource_key the cloud
        service adds them to the properties the resource key carries
        2) a cloud_endpoint to overwrite the default baseurl
        3) an cloud_request_origin to use when making requests
        4) timeout_seconds, how long each request to the cloud service
        waits, in seconds, which is 2 when it is missing or None
        5) an http_client to send the requests in place of a
        RequestClient. Its request method is given timeout_seconds when it
        has a parameter of that name.
        6) discovery_state, a copy of what an earlier engine discovered for
        the same credentials, as its discovery_state() gives it, either
        the JSON text or the dictionary it holds. The engine then makes
        no discovery request when it is built.

        See the Credentials section of the cloud request engine
        specification for the combinations that are accepted:
        https://github.com/51Degrees/specifications/blob/6570727d2af6967390d3c4fbec77b9cf0540d3f3/pipeline-specification/pipeline-elements/cloud-request-engine.md#credentials

        The constructor asks the cloud service for the accessible
        properties and the evidence keys, as warm_up says, so a built
        engine is ready to process. It raises CloudRequestException when
        the service refuses either request, for example because the
        resource key is not valid. It only warns when a request fails in a
        way that may pass, such as the service being unreachable, so a
        cloud outage does not stop the application starting. A request
        that times out is such a failure.

        @raise CloudRequestException: where the cloud service refuses either
        discovery request, with an answer from 400 to 499
        @raise ValueError: where a setting is one the engine cannot use, for
        example neither a resource_key nor a license_key, or a license_key
        with no requested_properties

        """

        super(CloudRequestEngine, self).__init__()

        self.datakey = "cloud"

        self.properties = {
            "cloud" : {
                "type": "string",
                "description": "raw JSON from the cloud service"
            }
        }

        # A credential read from an environment variable often arrives with
        # a trailing newline, and a value that is only whitespace is a
        # mistake rather than a key, so each one is trimmed and an empty
        # one counts as absent.
        self.resource_key = self.setting_text(settings, "resource_key")
        self.license_key = self.setting_text(settings, "license_key")

        # The names of the properties to ask for, each as "section.property"
        # in the case the cloud service uses, so comparison with its answer
        # is exact. The list is read on every request, so a caller may add
        # to it after the engine is built with add_requested_properties,
        # for example once the accessible properties say which client-side
        # properties the key carries.
        self.requested_properties = self.setting_names(
            settings, "requested_properties")

        self.check_credentials()

        # The sets of requested properties already reported as not covered
        # by the key, so the report is made once rather than on every
        # request. See report_properties_not_covered.
        self.reported_not_covered = set()

        # The endpoint is the cloud_endpoint setting, then the
        # _51DEGREES_CLOUD_ENDPOINT environment variable, then
        # cloud.51degrees.com. A host other than cloud.51degrees.com
        # would be used to (a) use an on premise web server, or (b) use
        # a privately hosted version of the 51Degrees cloud for
        # performance reasons. That is the private hosting option of
        # the cloud service, and both run the same service, so callers
        # work unchanged against either.
        if "cloud_endpoint" in settings:
            self.baseURL = settings["cloud_endpoint"]
        else:
            self.baseURL = _endpoint_from_environment()
            if self.baseURL is None:
                self.baseURL = Constants.BASE_URL_DEFAULT

        # Make sure if baseURL does not end with '/', one will be appended
        if not self.baseURL.endswith("/"):
            self.baseURL = self.baseURL + "/"

        # How long each request waits, so a cloud service that takes the
        # connection and never answers cannot hold the constructor or a
        # request.
        self.timeout_seconds = self.setting_timeout(settings)

        if "http_client" in settings:
            self.http_client = settings["http_client"]
        else:
            self.http_client = RequestClient(self.timeout_seconds)

        if "cloud_request_origin" in settings:
            self.cloud_request_origin = settings["cloud_request_origin"]
        else:
            self.cloud_request_origin = None

        self.exclude_from_messages = True

        # The evidence key filter, with the key list it was made from. See
        # get_evidence_key_filter.
        self._evidence_key_filter = None

        # The cloud service's answer to the accessible properties request,
        # kept for discovery_state().
        self._accessible_properties = None

        # Discovery runs now, so a built engine is ready to process and a
        # key the cloud service refuses fails here, not on a request. A
        # saved copy of an earlier engine's discovery takes its place.
        state = settings.get("discovery_state")
        if state is not None:
            self._use_discovery_state(state)
        else:
            self.warm_up()

    @staticmethod
    def setting_text(settings, name):

        """!
        A setting as trimmed text, or an empty string when it is missing,
        None or only whitespace.
        """

        value = settings.get(name)
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def setting_timeout(settings):

        """!
        The timeout_seconds setting, or the default when it is missing or
        None. A value that is not a number above zero is refused, because
        the requests library would refuse it on every request.
        """

        value = settings.get("timeout_seconds")
        if value is None:
            return Constants.TIMEOUT_SECONDS_DEFAULT
        # A bool is an int to Python, but True is not a number of seconds.
        # A socket refuses a timeout that is not finite.
        if (isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value) or value <= 0):
            raise ValueError(Constants.MESSAGE_TIMEOUT_NOT_POSITIVE.format(
                value, Constants.TIMEOUT_SECONDS_DEFAULT))
        return value

    @staticmethod
    def setting_names(settings, name):

        """!
        A setting holding property names, as a list of trimmed, non-empty,
        lower-cased names. The setting may be a list of names or one comma
        separated string, and a missing setting gives an empty list.

        The names are lower-cased because the cloud service lower-cases
        property names in its answer, so "Device.IsMobile" comes back as
        "ismobile" under "device".
        """

        value = settings.get(name)
        if value is None:
            return []
        if isinstance(value, str):
            value = value.split(",")
        names = []
        for entry in value:
            entry = str(entry).strip().lower()
            if entry != "":
                names.append(entry)
        return names

    def add_requested_properties(self, names):

        """!
        Add to the properties each request asks for, after the engine is
        built. The names are trimmed and lower-cased as the constructor
        does, so a name given in the case the documentation uses still
        matches the answer.

        @type names: list or string
        @param names: the names to add, as a list or one comma separated
        string, each as "section.property"
        """

        self.requested_properties.extend(
            self.setting_names({"names": names}, "names"))

    def check_credentials(self):

        """!
        Refuse a combination of resource key, licence key and requested
        properties that the cloud service would refuse on every request, so
        a deployment sees one configuration error when the engine is built
        rather than a failure on every request it serves.
        """

        has_resource_key = self.resource_key != ""
        has_license_key = self.license_key != ""
        has_requested_properties = len(self.requested_properties) > 0

        if has_resource_key == False and has_license_key == False:
            raise ValueError(Constants.MESSAGE_NO_CREDENTIAL)

        if has_resource_key == False and has_requested_properties == False:
            raise ValueError(Constants.MESSAGE_LICENSE_KEY_NEEDS_PROPERTIES)

    def get_credentials(self):

        """!
        The credentials to send with a request, as the keys the cloud
        service reads them from. A key that is not set is left out.

        @rtype: dict
        @return: Returns the credentials to send
        """

        credentials = {}
        if self.resource_key != "":
            credentials[Constants.RESOURCE_PARAMETER] = self.resource_key
        if self.license_key != "":
            credentials[Constants.LICENSE_PARAMETER] = self.license_key
        return credentials

    # The discovery results, each as the attribute that holds it and the
    # words a warning uses for it, in the order they are fetched.
    _DISCOVERY_RESULTS = (
        ("flow_element_properties", Constants.DISCOVERY_PROPERTIES),
        ("evidence_keys", Constants.DISCOVERY_EVIDENCE_KEYS))

    @cached_property
    def flow_element_properties(self):
        """!
        The properties the cloud service gives for the key in use, by the
        data key of each product, as get_engine_properties gives them. The
        constructor fetches them. If that failed, reading this asks again
        and raises if the cloud service fails again. The first answer is
        kept.
        """

        return self.get_engine_properties()

    @cached_property
    def evidence_keys(self):
        """!
        The evidence keys the cloud service accepts, fetched and kept as
        flow_element_properties is.
        """

        return self.get_evidence_keys()

    def known_flow_element_properties(self):
        """!
        flow_element_properties if the cloud service has given them, or
        None while discovery has not completed. This never makes a request,
        so a cloud engine can read it while the pipeline is built.

        @rtype: dict
        @return: the properties by product data key, or None
        """

        # cached_property keeps the value in the instance, under its own
        # name, once the value has been fetched.
        return vars(self).get("flow_element_properties")

    def discovery_state(self):
        """!
        What this engine discovered, being the evidence keys the cloud
        service accepts and its answer to the accessible properties
        request, as one JSON document. Give it as the discovery_state
        setting of another engine with the same credentials, and that
        engine is built without asking the cloud service. The document is
        the one the Java package's CloudDiscoveryState.toJson() writes.

        @rtype: str
        @return: the JSON document, or None while discovery has not
        completed
        """

        keys = vars(self).get("evidence_keys")
        if keys is None or self._accessible_properties is None:
            return None
        return json.dumps({
            Constants.DISCOVERY_STATE_EVIDENCE_KEYS: keys,
            Constants.DISCOVERY_STATE_ACCESSIBLE_PROPERTIES:
                self._accessible_properties})

    def _use_discovery_state(self, state):
        """!
        Take the discovery results from a copy discovery_state() gave,
        making no request.

        @raise ValueError: where the copy is not one discovery_state()
        gives
        """

        try:
            document = json.loads(state) if isinstance(state, (str, bytes)) \
                else state
            keys = document[Constants.DISCOVERY_STATE_EVIDENCE_KEYS]
            accessible = document[
                Constants.DISCOVERY_STATE_ACCESSIBLE_PROPERTIES]
            if not (isinstance(keys, list)
                    and all(isinstance(key, str) for key in keys)
                    and isinstance(accessible, dict)
                    and isinstance(accessible.get("Products"), dict)):
                raise ValueError()
            properties = self._read_accessible_properties(accessible)
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ValueError(Constants.MESSAGE_DISCOVERY_STATE_NOT_VALID) \
                from None
        self._accessible_properties = accessible
        # cached_property keeps each value in the instance under its own
        # name, so these are what reading them gives from now on.
        vars(self)["flow_element_properties"] = properties
        vars(self)["evidence_keys"] = list(keys)

    def warm_up(self):
        """!
        Ask the cloud service for the accessible properties and the
        evidence keys, which the constructor does so that a built engine is
        ready to process. Both requests are made whatever the first one
        answers, and a result already fetched is not asked for again.

        An answer from 400 to 499 means the cloud service refused the
        configuration, for example a resource key that is not valid, and
        asking again cannot change that, so the error is raised. Any other
        failure, such as the service being unreachable, a timeout or an
        answer of 500 or more, may pass, so it is given as a warning and
        the engine is still built. A result that could not be fetched is
        asked for again when the engine is next used, and a failure then is
        an error of that processing, which suppress_process_exceptions
        decides whether to raise.

        Raises CloudRequestException when the cloud service refused either
        request.
        """

        missing = []
        errors = []
        for name, description in self._DISCOVERY_RESULTS:
            try:
                getattr(self, name)
            except Exception as error:
                missing.append(description)
                errors.append(error)

        for error in errors:
            if self._is_refusal(error):
                raise error

        if errors:
            warnings.warn(Constants.MESSAGE_DISCOVERY_RETRY.format(
                " and ".join(missing),
                " ".join(self._describe(error) for error in errors)))

    @staticmethod
    def _is_refusal(error):
        """!
        Whether an error is the cloud service refusing a request, with a
        status from 400 to 499, rather than a failure that may pass.
        """

        return (isinstance(error, CloudRequestException)
                and Constants.HTTP_CLIENT_ERROR_MIN
                <= error.httpStatusCode < Constants.HTTP_SERVER_ERROR_MIN)

    def _describe(self, error):
        """!
        An error as text for a warning, with the licence key masked. The
        text of an error for several answered by the cloud service gives
        each of them.
        """

        return self.masked(
            "{}(\"{}\")".format(type(error).__name__, error))

    def _complete_discovery(self):
        """!
        Fetch any discovery result the constructor could not get, raising
        the error of a request that fails. Reading a result fetches it only
        when it is missing, so this makes no request once discovery has
        completed.
        """

        for name, _ in self._DISCOVERY_RESULTS:
            getattr(self, name)

    def get_evidence_keys(self):
        """!
        Internal function for getting evidence keys used by cloud engines
        @rtype: dict
        @return: Returns list of keys
        """
    
        evidenceKeyRequest = self.make_cloud_request('GET', self.baseURL + "evidencekeys")

        evidenceKeys = json.loads(evidenceKeyRequest)

        return evidenceKeys

    def get_evidence_key_filter(self):
        """!
        Instance of EvidenceKeyFilter based on evidence_keys. If the
        constructor could not fetch them, this asks the cloud service again
        and raises if it fails again, so that processing reports the
        failure rather than using a filter that accepts nothing.

        The filter is kept, as it is asked for once for each evidence key
        of every request. It is made again only when evidence_keys holds
        another list.

        @type: BasicListEvidenceKeyFilter
        @return: Returns BasicListEvidenceKeyFilter

        """

        keys = self.evidence_keys
        kept = self._evidence_key_filter
        if kept is None or kept[0] is not keys:
            kept = (keys, BasicListEvidenceKeyFilter(keys))
            self._evidence_key_filter = kept
        return kept[1]

    def get_engine_properties(self):
        """!
        Internal method to get properties for cloud engines from the cloud service
    
        @rtype: dict
        @return: Returns properties for all engines
        """

        # Get properties for all engines. A resource key alone goes in the
        # query string. A licence key identifies an account, so it is
        # posted in the body instead, where it stays out of request logs.
        # The cloud service reads both keys from either place, and answers
        # a licence key alone with every property the licence entitles.

        propertiesURL = self.baseURL + "accessibleProperties"

        if self.license_key == "":
            properties = self.make_cloud_request(
                'GET',
                propertiesURL + "?" + Constants.RESOURCE_PARAMETER + "="
                + self.resource_key)
        else:
            properties = self.make_cloud_request(
                'POST', propertiesURL, self.get_credentials())

        properties = json.loads(properties)
        flowElementProperties = self._read_accessible_properties(properties)
        self._accessible_properties = properties
        return flowElementProperties

    @staticmethod
    def _read_accessible_properties(properties):
        """!
        The properties of each product, by data key and then by property
        name, from the cloud service's answer to the accessible properties
        request.
        """

        flowElementProperties = {}

        # Change indexes to be by name
        for datakey, elementProperties in properties["Products"].items():

            flowElementProperties[datakey] = {}

            engine_properties = elementProperties["Properties"]

            for engineProperty in engine_properties:

                # Lowercase keys

                engineProperty =  {k.lower(): v for k, v in engineProperty.items()}

                flowElementProperties[datakey][engineProperty["name"]] = engineProperty
               
        return flowElementProperties

    def validate_response(
        self,
        cloud_response: requests.Response,
        check_for_error_messages=True,
    ):
        """!
        Validate the JSON response from the cloud service. Each entry in
        the warnings list of the response is given as a warning, with the
        licence key masked, and does not fail the request.

        @type: Response
        @param: Response returned from the cloud service.
        @raise CloudRequestException: where the response is not JSON, holds
        errors, has no data, or has a status other than 200
        """

        has_data = cloud_response.text and cloud_response.text.strip()
        messages = []

        if has_data and check_for_error_messages:
            # The status goes with the error, so a caller can tell a
            # refusal from a failure that may pass.
            try:
                json_response = cloud_response.json()
            except (JSONDecodeError, requests.exceptions.JSONDecodeError):
                raise CloudRequestException(self.masked(
                    f'Cloud request engine properties list request returned code "{cloud_response.status_code}"'
                    f' with non-JSON content "{cloud_response.text}"'
                ), cloud_response.status_code)
            except Exception as e:
                raise CloudRequestException(self.masked(
                    f'Cloud request engine properties list request returned code "{cloud_response.status_code}"'
                    f' with content "{cloud_response.text}".\nError: "{type(e).__name__}: {e}"'
                ), cloud_response.status_code)

            has_errors = "errors" in json_response and len(json_response["errors"])
            has_data = len(json_response) > (1 if has_errors else 0)

            # Each entry of the errors list is the text of one error.
            if has_errors:
                messages.extend(
                    entry if isinstance(entry, str) else json.dumps(entry)
                    for entry in json_response["errors"])

            self._warn_response_warnings(json_response)

        # If there were no errors but there was also no other data
        # in the response then add an explanation to the list of
        # messages.
        if not messages and not has_data:
            message = Constants.MESSAGE_NO_DATA_IN_RESPONSE.format(
                mask_licence_keys_in_text(cloud_response.url))
            messages.append(message)

        # If there were no errors returned but the response code was non
        # success then throw an exception.
        if not messages and cloud_response.status_code != 200:
            message = Constants.MESSAGE_ERROR_CODE_RETURNED.format(
                self.baseURL,
                cloud_response.status_code,
                cloud_response.json(),
            )
            messages.append(message)

        if not messages:
            return

        # One error is raised with its text as the message. Several are
        # raised together, one exception for each in the exceptions of the
        # one raised.
        errors = [
            CloudRequestException(
                self.masked(Constants.EXCEPTION_CLOUD_ERROR.format(message)),
                cloud_response.status_code,
                cloud_response.headers,
            )
            for message in messages
        ]
        if len(errors) == 1:
            raise errors[0]
        raise CloudRequestException(
            Constants.EXCEPTION_CLOUD_ERRORS_MULTIPLE,
            cloud_response.status_code,
            cloud_response.headers,
            errors,
        )

    def masked(self, text):

        """!
        Text from or about a cloud answer with the licence key in use shown
        only as its last four characters. The cloud service names the key in
        some of its errors, and a URL may carry it in its query.
        """

        text = mask_licence_keys_in_text(text)
        if self.license_key != "":
            text = text.replace(
                self.license_key, mask_licence_key(self.license_key))
        return text

    def _warn_response_warnings(self, json_response):

        """!
        Give each entry in the warnings list of a cloud answer as a
        warning, with the licence key masked. An answer with no such list
        gives none.
        """

        if not isinstance(json_response, dict):
            return
        entries = json_response.get("warnings")
        if not isinstance(entries, list):
            return
        for entry in entries:
            warnings.warn(self.masked(str(entry)))

    def make_cloud_request(self, type, url, content = None):

        """!    
        @type url: string
        @param url
        
        @rtype: dict
        @return Returns dict with data and error properties error contains any errors from the request, data contains the response
        """

        if _takes_timeout(self.http_client):
            cloudResponse = self.http_client.request(
                type, url, content, self.cloud_request_origin,
                timeout_seconds=self.timeout_seconds)
        else:
            cloudResponse = self.http_client.request(
                type, url, content, self.cloud_request_origin)

        self.validate_response(cloudResponse)

        return cloudResponse.text           

    def process_internal(self, flowdata):

        """!
        Processing function for the CloudRequestEngine
        Makes a request to the cloud service with the supplied resource key
        and evidence and returns a JSON object that is then parsed by cloud engines
        placed later in the pipeline

        A discovery result the constructor could not fetch is fetched
        first. If the cloud service fails again, the error is raised and no
        request for data is made, so the pipeline's
        suppress_process_exceptions decides what the caller sees.

        @type FlowData: FlowData
        @param FlowData: Returns a JSON object that is then parsed by cloud engines

        """

        self._complete_discovery()

        # A resource key names the route. A licence key
        # alone has no resource key to put there, so it uses the data
        # endpoint that takes none and travels in the body with the list
        # of properties wanted.
        if self.resource_key != "":
            url = self.baseURL + self.resource_key + ".json?"
        else:
            url = self.baseURL + Constants.LICENSE_DATA_PATH

        content = self.get_content(flowdata)
        content.update(self.get_credentials())
        if len(self.requested_properties) > 0:
            content[Constants.VALUES_PARAMETER] = ",".join(
                self.requested_properties)

        result = self.make_cloud_request('POST', url, content)

        if len(self.requested_properties) > 0:
            self.report_properties_not_covered(result)

        data = AspectDataDictionary(self, {"cloud" : result})

        flowdata.set_element_data(data)

        return

    def process(self, flowdata):

        """!
        Process as any engine does, the cache included, then give the data
        under cloud-response, the key the specification gives, as well as
        under the engine's datakey, cloud, which is deprecated. Both keys
        give the same object. The datakey stays cloud, so the pipeline
        still names the engine by it and the JSON for the browser still
        leaves its data out.

        @type flowdata: FlowData
        @param flowdata: the FlowData to process
        """

        result = super(CloudRequestEngine, self).process(flowdata)

        # FlowData keeps each element's data under its datakey in lower case.
        data = flowdata.data.get(self.datakey.lower())
        if data is not None:
            flowdata.data[Constants.RESPONSE_DATA_KEY] = data

        return result

    def is_cacheable(self, data):

        """!
        A response whose JSON has a top-level member named fodid, in any
        case, holds a 51Did created for the one request that asked for it,
        so it is neither stored in the cache nor served from it. A fodid
        below the top level is not one, and a response that cannot be read
        as a JSON object is cached as before.

        @type data: ElementData
        @param data: A response the engine has just made, or one found in
        the cache

        @rtype: bool
        @return: False if the response holds a fodid
        """

        try:
            answer = json.loads(data.get("cloud"))
        except (AttributeError, JSONDecodeError, KeyError, TypeError,
                ValueError):
            return True
        if not isinstance(answer, dict):
            return True
        return not any(str(name).lower() == "fodid" for name in answer)

    def report_properties_not_covered(self, result):

        """!
        Compare the properties a request asked for with the ones its answer
        carries, and warn once about any it left out.

        With a licence key, the cloud service drops a property the licence
        key does not cover without naming it, whenever the request also
        asked for a property the key does cover, so the engine has to
        notice the difference itself. With a resource key and no licence
        key, a property no licence grants comes back as null with a reason,
        so a name left out is not a property, and the warning says that
        instead. A property that is present but null counts as answered,
        because it carries a nullreason beside it saying why it has no
        value on this request, which is a different matter from
        entitlement. The answer cannot change while the keys and the list
        stay the same, so each distinct list is reported once.

        @type result: string
        @param result: the JSON text the cloud service answered with
        """

        requested = frozenset(self.requested_properties)
        if requested in self.reported_not_covered:
            return

        try:
            answer = json.loads(result)
        except (AttributeError, JSONDecodeError, TypeError, ValueError):
            # validate_response has already dealt with an answer that is
            # not JSON, so there is nothing to compare here.
            return

        # An answer that parses but is not an object, such as an array,
        # has no sections to look in. Reporting must not fail the request,
        # which succeeded, so there is nothing to say.
        if isinstance(answer, dict) == False:
            return

        not_covered = []
        for name in sorted(requested):
            section, _, property_name = name.partition(
                Constants.EVIDENCE_SEPERATOR)
            section_values = answer.get(section)
            if (isinstance(section_values, dict) == False
                    or property_name not in section_values):
                not_covered.append(name)

        self.reported_not_covered.add(requested)

        if len(not_covered) > 0:
            message = (Constants.MESSAGE_PROPERTIES_NOT_COVERED
                       if self.license_key != ""
                       else Constants.MESSAGE_PROPERTIES_NOT_KNOWN)
            warnings.warn(message.format(", ".join(not_covered)))

    def get_content(self, flowData):

        """!
        Generate the Content to send in the POST request. One name under
        several prefixes is sent once, with the value of the prefix that
        evidence.md ranks highest, being query, header, cookie, server,
        fiftyone and location, then any other prefix alphabetically. The
        groups are added lowest precedence first, so a later value replaces
        an earlier one, and a replacement by a key other than a query key
        is logged as a warning.

        The engine sends every evidence value in the flow data, including
        the values no element in the pipeline accepts, because what the
        cloud service uses changes over time and knowing about the other
        evidence is important to continued optimization. The reserved names
        and the web request view are left out.

        @param: flowData: FlowData
        @return: Evidence Dictionary
        """

        queryData = {}

        evidence = self.sendable_evidence(flowData.evidence)
        # Add the other evidence lowest precedence first.
        self.add_query_data(queryData, evidence, self.get_selected_evidence(evidence, Constants.EVIDENCE_OTHER))
        # Add cookie evidence.
        self.add_query_data(queryData, evidence, self.get_selected_evidence(evidence, Constants.EVIDENCE_COOKIE_PREFIX))
        # Add header evidence.
        self.add_query_data(queryData, evidence, self.get_selected_evidence(evidence, Constants.EVIDENCE_HTTPHEADER_PREFIX))
        # Add query evidence.
        self.add_query_data(queryData, evidence, self.get_selected_evidence(evidence, Constants.EVIDENCE_QUERY_PREFIX))
        return queryData

    def sendable_evidence(self, evidence):

        """!
        The evidence the engine sends, being every value in the flow data,
        whether an element accepted it or not, apart from the web request
        view. The reserved names are left out by add_query_data, which
        warns as it does so. An accepted value wins over a set aside one of
        the same key.

        @param evidence: The flow data's Evidence
        @return: The evidence keys and values to send
        """

        sendable = {}
        # An older fiftyone_pipeline_core sets nothing aside.
        unaccepted = getattr(evidence, "get_unaccepted", dict)()
        for source in (unaccepted, evidence.get_all()):
            for key, value in source.items():
                if str(key).lower() != HTTP_REQUEST_KEY:
                    sendable[key] = value
        return sendable

    def add_query_data(self, query_data, all_evidence, evidence):

        """!
        Add query data to the evidence.

        @param: query_data: The destination dictionary to add query data to.
        @param all_evidence: All evidence in the flow data. This is used to report which evidence
        keys are conflicting.
        @param evidence: Evidence to add to the query Data.
        """        

        for evidenceKey, evidenceValue in evidence.items():

            # The prefix is the text before the first separator, and the
            # name sent is the rest of the key in the letter case given, as
            # .NET's AddQueryData takes it. A key with no separator is both.
            prefix, separator, suffix = evidenceKey.partition(
                Constants.EVIDENCE_SEPERATOR)
            if not separator:
                suffix = evidenceKey
            prefix = prefix.lower()

            # The service reads its credentials and the list of requested
            # properties from these names, so evidence carrying one of them
            # would sit beside the engine's own values with no way to know
            # which one the service applied. Leave such evidence out, and
            # say so as the conflict case below does, so a caller who set
            # it expecting an effect can see why there was none. The value
            # is not logged, as it may be a credential.
            if suffix.lower() in Constants.RESERVED_EVIDENCE_SUFFIXES:
                warnings.warn(
                    Constants.WARNING_RESERVED_EVIDENCE.format(evidenceKey))
                continue

            # Evidence keys ignore letter case, so a name already added in
            # other letters is the same name, and the later, higher
            # precedence value replaces it under its own spelling.
            existing = next((name for name in query_data
                             if name.lower() == suffix.lower()), None)

            # Check and add the evidence to the query parameters.
            if existing is None:
                query_data[suffix] = evidenceValue
            # If the queryParameter exists already.
            else:
                # Get the conflicting pieces of evidence and then log a 
                # warning, if the evidence prefix is not query. Otherwise a
                # warning is not needed as query evidence is expected 
                # to overwrite any existing evidence with the same suffix.
                if (prefix.lower() != Constants.EVIDENCE_QUERY_PREFIX):
                    conflicts = {}
                    for key, value in all_evidence.items(): 
                        if(key.lower() != evidenceKey.lower() and suffix.lower() in key.lower()):
                            conflicts[key] = value

                    warningMessage = Constants.WARNING_MESSAGE \
                                        .format(evidenceKey, evidenceValue) 
                        
                    conflictStr = ', '.join('{}:{}'.format(key, value) \
                                for key, value in conflicts.items())
                    
                    if conflictStr:
                        warnings.warn(warningMessage + conflictStr)
                    
                # Overwrite the existing queryParameter value.
                del query_data[existing]
                query_data[suffix] = evidenceValue

    def get_selected_evidence(self, evidence, type):
        
        """!
        Get evidence with specified prefix.

        @param evidence: All evidence in the flow data.
        @param type: Required evidence key prefix
        """

        selected_evidence = {}

        if type == Constants.EVIDENCE_OTHER:
            for key, value in evidence.items():
                if (not self.key_has_prefix(key, Constants.EVIDENCE_QUERY_PREFIX) and \
                        not self.key_has_prefix(key, Constants.EVIDENCE_HTTPHEADER_PREFIX) and \
                            not self.key_has_prefix(key, Constants.EVIDENCE_COOKIE_PREFIX)):
                    selected_evidence[key] = value
            # Lowest precedence first, so the value added last wins.
            selected_evidence = dict(sorted(
                selected_evidence.items(),
                key=lambda item: self.other_prefix_rank(item[0]),
                reverse=True))

        else:
            for key, value in evidence.items():
                if self.key_has_prefix(key, type):
                    selected_evidence[key] = value
            
        return selected_evidence

    def other_prefix_rank(self, key):

        """!
        The sort key of an evidence key that is not query, header or cookie
        evidence, where a lower one wins. server, fiftyone and location
        come first, in the order evidence.md lists them, then any other
        prefix alphabetically, all ignoring letter case.

        @param key: The evidence key
        @return: A tuple that sorts higher precedence first
        """

        prefix = key.partition(Constants.EVIDENCE_SEPERATOR)[0].lower()
        if prefix in Constants.OTHER_PREFIX_PRECEDENCE:
            return (Constants.OTHER_PREFIX_PRECEDENCE.index(prefix), "",
                    key.lower())
        return (len(Constants.OTHER_PREFIX_PRECEDENCE), prefix, key.lower())

    def key_has_prefix(self, itemKey, prefix):

        """!
        Check that the key of a KeyValuePair has the given prefix.

        @param itemKey: Key to check
        @param prefix: The prefix to check for.
        @return: True if the key has the prefix.
        """

        key = itemKey.split(Constants.EVIDENCE_SEPERATOR)
        return key[0].lower() == prefix.lower()
