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

import random
import re
import json
import gzip
import platform
import datetime
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version

import requests
from fiftyone_pipeline_engines.engine import Engine

from .share_usage_evidencekeyfilter import ShareUsageEvidenceKeyFilter, \
    ShareUsageTrackerEvidenceKeyFilter
from .share_usage_tracker import ShareUsageTracker

# The maximum length of a piece of evidence's value which can be
# added to the usage data being sent.
SHARE_USAGE_MAX_EVIDENCE_LENGTH = 10000

SHARE_USAGE_VERSION = '1.1'

# The default number of seconds to wait for the server connection before failing the request when sending usage data
REQUEST_TIMEOUT = 60


class ShareUsage(Engine):
    def __init__(
        self,
        interval = 1200,
        requested_package_size = 10,
        cookie = None,
        query_whitelist = [],
        header_blacklist = [],
        share_percentage = 1,
        endpoint = "https://devices-v4.51degrees.com/new.ashx",
        request_timeout=REQUEST_TIMEOUT,
        share_all = False,
        track_session = False):
        """!
        Constructor for ShareUsage element
        
        @type interval: int
        @param interval: If exactly the same evidence values are seen 
        multiple times within this time limit (in seconds) then they 
        will only be shared once.
        @type requested_package_size: int
        @param requested_package_size: The usage element will group data into 
        single requests before sending it. This setting controls the minimum 
        number of entries before data is sent. If you are sharing large 
        amounts of data, increasing this value is recommended in order to 
        reduce the overhead of sending HTTP messages.
        For example, the 51Degrees cloud service uses a value of 2500.
        @type cookie: string
        @param cookie: The name of the cookie that holds the session id.
        It has no effect unless track_session is True. The cookie itself
        is not shared unless share_all is True.
        @type track_session: bool
        @param track_session: If True, the cookie named by cookie is used
        to tell user sessions apart, so evidence already shared is shared
        again when it comes from a new session. False by default. It
        needs cookie to be set, and has no effect when share_all is True,
        because every cookie is then shared and used to find repeats.
        @type query_whitelist: list
        @param query_whitelist: By default query string and HTTP form
        parameters are not shared unless prefixed with '51D_'.
        If you need to share query string parameters, a list can be
        specified here. None shares every parameter.
        @type header_blacklist: list
        @param header_blacklist: By default, all HTTP headers
        except Cookie are shared.
        Individual headers can be excluded from sharing by adding them
        to this list.
        @type share_percentage : float
        @param share_percentage: approximate proportion of requests to
        be shared. 1 = 100%, 0.5 = 50%, etc..
        @type share_all: bool
        @param share_all: If True, all evidence is shared apart from the
        email address, the salt used for hashed email identifiers, and the
        request's query string and path. False by default.
        """

        super(ShareUsage, self).__init__()

        self.query_whitelist = query_whitelist

        self.header_blacklist = header_blacklist

        self.datakey = "shareusage"

        self.interval = interval
        self.requested_package_size = requested_package_size
        self.cookie = cookie
        self.share_percentage = share_percentage
        self.endpoint = endpoint
        self.request_timeout = request_timeout
        self.share_all = share_all
        self.track_session = track_session

        # The session id and sequence number are kept in evidence, as the
        # usage data carries them separately.
        included = None if query_whitelist is None else \
            list(query_whitelist) + ["session-id", "sequence"]

        # When sessions are tracked, the pipeline keeps the session cookie
        # for the tracker. The data sent leaves it out unless all evidence
        # is shared.
        self.evidence_key_filter = ShareUsageEvidenceKeyFilter(
            cookie, included, header_blacklist, track_session, share_all)
        self.data_evidence_key_filter = ShareUsageEvidenceKeyFilter(
            cookie, included, header_blacklist, False, share_all)
        self.tracker_evidence_key_filter = \
            ShareUsageTrackerEvidenceKeyFilter(
                cookie, included, header_blacklist, track_session,
                share_all)

        # Add the share usage tracker which detects when
        # to send up sharing data

        self.tracker = ShareUsageTracker(interval = interval)

        # Initialise share data list 
        self.share_data = []

        self.constant_xml = None

        # Reusable thread pool for sending usage in background
        # According to the doc on ThreadPoolExecutor - all threads will be joined before the interpreter can exit
        # this ensures that all the data will be sent correctly before the actual exit happens

        self.thread_pool = ThreadPoolExecutor(thread_name_prefix='ShareUsage')

    def __del__(self):
        self.thread_pool.shutdown(wait=True)

    def close(self):

        """!
        Wait for any usage data already being sent, then stop the threads
        that send it. The pipeline calls this when it is closed.

        """

        super(ShareUsage, self).close()
        self.thread_pool.shutdown(wait=True)

    def get_constant_xml(self):
        if self.constant_xml is None:
            coreVersion = version("fiftyone_pipeline_core")
            osVersion = f"{ReplacedString(platform.system()).result} {ReplacedString(platform.release()).result}"
            pyVersion = ReplacedString(platform.python_version()).result

            xml = ""

            # The version number of the Pipeline API
            xml += f"<Version>{coreVersion}</Version>"
            # Write Pipeline information
            # The product name
            xml += "<Product>Pipeline</Product>"
            # The flow elements in the current pipeline
            for flow_element in self.get_flow_elements():
                xml += f"<FlowElement>{flow_element}</FlowElement>"
            xml += "<Language>Python</Language>"
            # The software language version
            xml += f"<LanguageVersion>{pyVersion}</LanguageVersion>"
            # The OS name and version
            xml += f"<Platform>{osVersion}</Platform>"
            self.constant_xml = xml
        return self.constant_xml

    def get_flow_elements(self):
        if len(self.pipelines) == 1:
            list = []
            
            for flow_element in self.pipelines[0].flow_elements:
                list.append(type(flow_element).__name__)
            return list
        else:
            # This element has somehow been registered to too
            # many (or zero) pipelines.
            # This means we cannot know the flow elements that
            # make up the pipeline so a warning is logged
            # but otherwise, the system can continue as normal.
            self._log(
                "warning",
                "Share usage element registered "
                f"to {'too many' if len(self.pipelines) > 0 else 'no'}"
                " pipelines. Unable to send share usage information.")
            return []


    def get_evidence_key_filter(self):

        """!

        The share useage element comes with its own evidence
        key filter that uses the whitelists and blacklists to
        determine which evidence to share    
    
        """

        return self.evidence_key_filter

    def share_send_usage(self):
        """!
        Internal method to send the share usage bundle to the 51Degrees servers
        """

        share_data = self.share_data
        self.share_data = []

        data = f'<Devices version="{SHARE_USAGE_VERSION}">{"".join(share_data)}</Devices>'

        self.thread_pool.submit(self.send_thread, self.endpoint, data)

    def send_thread(self, endpoint, data):
        data = gzip.compress(bytearray(data, encoding='utf8'))

        # setting a reasonable time out and catching any exceptions
        try:
            requests.post(endpoint, headers={"Content-Encoding": "gzip", "Content-Type": "text/xml"}, data=data,
                          timeout=self.request_timeout)
        except Exception as e:
            print(e)
            self._log(
                "error",
                f"ShareUsage failed sending {len(data)} bytes of data: {e}"
            )

    def add_to_share_usage(self, data):
        """!
        Internal method which adds to the share usage bundle (generating XML)
        @type key: dict
        @param key: data value store of current evidence in FlowData
        """

        xml = ""
        
        xml += "<Device>"

        # --- write invariant data
        xml += self.get_constant_xml()

        # --- write variable data
        # The SessionID used to track a series of requests
        xml += record_element("SessionId", data.session_id)
        # The sequence number of the request in a series of requests.
        xml += f"<Sequence>{data.sequence}</Sequence>"
        # The client IP of the request
        xml += record_element("ClientIP", data.client_ip)

        # The UTC date and time this entry was written, to the second.
        date = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S")
        xml += f"<DateSent>{date}</DateSent>"

        # Write all other evidence data that has been included. The prefix,
        # or a key with no prefix, is the element name. An entry whose
        # element name is not an XML name is left out, because it would make
        # the whole batch unreadable.
        for category_key, category_value in data.evidence_data.items():
            for entry_key, entry_value in category_value.items():
                if len(category_key) > 0:
                    if XML_NAME.match(category_key):
                        xml += record_element(
                            category_key, entry_value, entry_key)
                elif XML_NAME.match(entry_key):
                    xml += record_element(entry_key, entry_value)

        xml += "</Device>"
 
        self.share_data.append(xml)

        # Send share usage data if data size greater than requested
        # package size
        if len(self.share_data) >= self.requested_package_size:
            self.share_send_usage()

    def process_internal(self, flow_data):

        """!

        Internal process method which uses the ShareUsageTracker
        to determine whether to add usage data to a batch and adds it if necessary.
        @type flow_data: FlowData
        @param flow_data: FlowData to process

        """
        
        if random.uniform(0, 1) <= self.share_percentage:
            cachekey = self.tracker_evidence_key_filter.filter_evidence(flow_data.evidence.get_all())
            cachekey = json.dumps(cachekey)
            share = self.tracker.track(cachekey) 
            if share:
                self.tracker.set_cache_value(cachekey)
                self.add_to_share_usage(self.get_data_from_evidence(flow_data))

    def get_data_from_evidence(self, flow_data):
        """!    
         Creates a ShareUsageData instance populated from the evidence
         within the flow data provided.
         @param {FlowData} flowData the flow data containing the evidence to use
         @returns a new ShareUsageData instance, populated from the evidence
         provided 
        """
        data = ShareUsageData()

        for key, value in flow_data.evidence.get_all().items():
            if key == 'server.client-ip':
                # The client IP is dealt with separately for backwards
                # compatibility purposes.
                data.client_ip = value
            elif key == 'query.session-id':
                # The SessionID is dealt with separately.
                data.session_id = value
            elif key == 'query.sequence':
                # The Sequence is dealt with separately.
                try:
                    sequence = int(value)
                    data.sequence = sequence
                except:
                    self._log(
                        "error",
                        f"The value '{value}' could not be parsed to an integer.")
            else:
                # Check if we can send this piece of evidence
                if self.data_evidence_key_filter.filter_evidence_key(key):
                    data.try_add(key, value)

        return data


# The characters that XML 1.0 section 2.2 allows, as ranges of code points.
VALID_XML_RANGES = (
    (0x9, 0xA), (0xD, 0xD), (0x20, 0xD7FF), (0xE000, 0xFFFD),
    (0x10000, 0x10FFFF))

# The characters that are written as entities in element text.
XML_ENTITIES = {
    '&': '&amp;',
    '"': '&quot;',
    "'": '&apos;',
    '<': '&lt;',
    '>': '&gt;',
}


def is_valid_xml_char(code):
    return any(low <= code <= high for low, high in VALID_XML_RANGES)


# The characters XML 1.0 allows in a name, without the colon, which names a
# namespace.
XML_NAME_START = (
    "A-Z_a-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u02ff\u0370-\u037d"
    "\u037f-\u1fff\u200c-\u200d\u2070-\u218f\u2c00-\u2fef\u3001-\ud7ff"
    "\uf900-\ufdcf\ufdf0-\ufffd\U00010000-\U000effff")
XML_NAME = re.compile(
    "[" + XML_NAME_START + "][" + XML_NAME_START +
    "\\-.0-9\u00b7\u0300-\u036f\u203f-\u2040]*\\Z")


def record_element(tag, value, name=None):
    """!
    One element of a usage sharing record. The value, and the Name attribute
    when there is one, are made to fit the XML by ReplacedString, and the
    element is marked escaped or truncated when either changed.
    """
    replaced = ReplacedString(value)
    escaped = replaced.escaped
    xml = "<" + tag
    if name is not None:
        replaced_name = ReplacedString(name)
        escaped = escaped or replaced_name.escaped
        xml += ' Name="' + replaced_name.result + '"'
    if escaped:
        xml += ' escaped="true"'
    if replaced.truncated:
        xml += ' truncated="true"'
    return xml + ">" + replaced.result + "</" + tag + ">"


class ReplacedString:
    """!
    Makes an Evidence value fit in the usage sharing XML. The value is cut to
    SHARE_USAGE_MAX_EVIDENCE_LENGTH characters (code points, so a character is
    never split), a character XML 1.0 does not allow is written as a backslash,
    "x" and its code in four lower-case hexadecimal digits, and the markup
    characters are written as entities. `escaped` and `truncated` say what
    changed.
    """
    def __init__(self, text):
        self.result = ""
        self.escaped = False
        self.truncated = False
        if text:
            if not isinstance(text, str):
                text = str(text)
            self.truncated = len(text) > SHARE_USAGE_MAX_EVIDENCE_LENGTH
            self.result = "".join(
                map(self.map_char, text[0:SHARE_USAGE_MAX_EVIDENCE_LENGTH]))

    def map_char(self, char):
        code = ord(char)
        if not is_valid_xml_char(code):
            self.escaped = True
            return "\\x%04x" % code
        return XML_ENTITIES.get(char, char)

class ShareUsageData:
    """!
    Internal class that is used to store details of data in memory
    prior to it being sent to 51Degrees.
    """

    def __init__(self):
        self.evidence_data = {}
        self.session_id = ""
        self.client_ip = ""
        self.sequence = ""

    def try_add(self, key, value):
        # Get the category and field names from the evidence key.
        category = ""
        field = key

        first_separator = key.find(".")
        if first_separator > 0:
            category = key[0:first_separator]
            field = key[first_separator + 1:len(key)]

        # Add the evidence to the dictionary.
        if category in self.evidence_data:
            category_dict = self.evidence_data[category]
        else:
            category_dict = {}
            self.evidence_data[category] = category_dict

        category_dict[field] = value
