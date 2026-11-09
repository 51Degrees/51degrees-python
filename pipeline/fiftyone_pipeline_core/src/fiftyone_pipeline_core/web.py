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

import hashlib
import json
import re

from flask import make_response, request

# How long the browser alone may keep a client-side response to a request
# whose processing recorded no errors, unless the caller gives another time.
CLIENT_SIDE_MAX_AGE_SECONDS = 1800

# The Cache-Control of a client-side response to a request whose processing
# recorded errors. It goes with no ETag, so a browser that kept the response
# has nothing to revalidate with and asks again in full once processing
# works, rather than having the faulty response confirmed by a 304.
_CACHE_CONTROL_AFTER_ERRORS = "private, no-cache"

# The headers a browser adds when it revalidates or reloads. They differ
# between a request and its revalidation and no element uses them, so they
# are left out of the ETag and the Vary header.
_REVALIDATION_HEADERS = frozenset((
    "cache-control", "if-match", "if-modified-since", "if-none-match",
    "if-range", "if-unmodified-since", "pragma"))

# An entity tag of RFC 9110 section 8.8.3, being an optional W/ and an
# opaque tag in double quotes of visible characters other than the double
# quote. The second group is the opaque tag without its quotes.
_ENTITY_TAG = re.compile(r'(W/)?"([\x21\x23-\x7e\x80-\xff]*)"')

# The optional whitespace around the commas of a list, RFC 9110 section
# 5.6.3.
_OWS = " \t"

def webevidence(request):

    """!
    Get evidence from a web request (gets headers, cookies, query parameters
    and the fields of a posted form)
    
    @type request: Request 
    @param request: A Request object
    @rtype dict
    @return A dictionary of web evidence that can be using in flowdata.evidence.add_from_dict()

    """

    webevidence = {}

    for header in request.headers:
        webevidence["header." + header[0].lower()] = header[1]

    for cookieKey, cookieValue in request.cookies.items():
        webevidence["cookie." + cookieKey] = cookieValue

    for query,value in request.args.items():

        webevidence["query." + query] = value

    # Form fields are query evidence too, as in the other languages' web
    # integrations. The client script posts the results of its snippets, the
    # session id and the sequence as a form body, so without this none of
    # them reached the pipeline. They are added after the query string, so
    # a value the script sent in its body replaces one in the URL. Flask
    # only fills request.form for a form content type, so any other body is
    # left alone.
    if request.method == "POST":
        for field, value in request.form.items():

            webevidence["query." + field] = value

    webevidence["server.client-ip"] =  request.remote_addr

    webevidence["server.host-ip"] =  request.host

    if (request.is_secure):
        webevidence["header.protocol"] = "https"
    else:
        webevidence["header.protocol"] = "http"

    return webevidence

def set_response_header(flowData, response):
    
    """!
    Set UACH response header in web response (sets Accept-CH header in response)
    
    @type response: Response 
    @param response: A Response object
    @param response_header_dict: Dictionary containing response header key and values to be set
    @rtype response
    @return A response object containing headers with non null values in response

    """
    
    # Get response headers dictionary containing key values to be set in response  
    response_header_dict = flowData["set-headers"]["responseheaderdictionary"]
    for response_key, response_value in response_header_dict.items():
        response_value = response_value.replace(",", ", ")
        if response_value != "":
            response.headers[response_key] = response_value

    return response

def javascript_response(
        pipeline, request, max_age_seconds=CLIENT_SIDE_MAX_AGE_SECONDS):

    """!
    Process a request for the client-side JavaScript and answer with the
    JavaScript the pipeline's JavaScriptBuilder writes, with the cache headers
    the web integration specification sets.

    The ETag is a weak entity tag, W/"...", hashed from the evidence the
    request supplied that the pipeline's elements accept. A GET or HEAD
    request whose If-None-Match header matches it, by the weak comparison of
    RFC 9110 section 13.1.2, gets a 304 without being processed, so a
    browser keeps a good copy while processing fails. A request by any other
    method whose If-None-Match matches, such as a POST to the JSON endpoint,
    gets 412 Precondition Failed. An If-None-Match that is neither "*" nor a
    list of entity tags matches nothing. Otherwise the response carries
    'Cache-Control: max-age=1800, private', or the max age given, and the
    ETag, or 'Cache-Control: private, no-cache' and no ETag when processing
    recorded errors. Both carry a Vary header naming the request headers the
    pipeline's elements accept.

    @type pipeline: Pipeline
    @param pipeline: A pipeline holding the JavaScriptBuilder
    @type request: Request
    @param request: The request for the JavaScript
    @type max_age_seconds: int
    @param max_age_seconds: How long the browser may keep the response
    @rtype Response
    @return The response to send
    """

    return _client_side_response(
        pipeline, request,
        lambda flowdata: flowdata.javascriptbuilder.javascript,
        "application/x-javascript", max_age_seconds)

def json_response(
        pipeline, request, max_age_seconds=CLIENT_SIDE_MAX_AGE_SECONDS):

    """!
    Process a request from the client-side JavaScript and answer with the
    JSON the pipeline's JSONBundler writes, with the same cache headers as
    javascript_response.

    @type pipeline: Pipeline
    @param pipeline: A pipeline holding the JSONBundler
    @type request: Request
    @param request: The request from the client-side JavaScript
    @type max_age_seconds: int
    @param max_age_seconds: How long the browser may keep the response
    @rtype Response
    @return The response to send
    """

    return _client_side_response(
        pipeline, request,
        lambda flowdata: json.dumps(flowdata.jsonbundler.json),
        "application/json", max_age_seconds)

def _client_side_response(
        pipeline, request, content, content_type, max_age_seconds):

    cache_control = "max-age=" + str(int(max_age_seconds)) + ", private"
    flowdata = pipeline.create_flowdata()
    try:
        evidence = webevidence(request)
        flowdata.evidence.add_from_dict(evidence)

        # From the request's own evidence, because processing adds to it.
        # The sequence element gives a request with no session id a new one.
        opaque_tag = _opaque_tag(pipeline, evidence)
        # Weak, because the response can change while the evidence does not,
        # for example when the data file is updated (RFC 9110 section 8.8.3).
        etag = 'W/"' + opaque_tag + '"'
        vary = _vary(pipeline, request)

        if _if_none_match_matches(
                request.headers.get("If-None-Match"), opaque_tag):
            if request.method not in ("GET", "HEAD"):
                # RFC 9110 section 13.1.2 allows a 304 for GET and HEAD only.
                response = make_response("", 412)
                response.headers.pop("Content-Type", None)
                return response
            # With the headers of a good response that RFC 9110 section
            # 15.4.5 asks a 304 to repeat.
            response = make_response("", 304)
            response.headers.pop("Content-Type", None)
            response.headers["Cache-Control"] = cache_control
            response.headers["ETag"] = etag
        else:
            flowdata.process()
            response = make_response(content(flowdata))
            response.headers["Content-Type"] = content_type
            if flowdata.errors:
                response.headers["Cache-Control"] = _CACHE_CONTROL_AFTER_ERRORS
            else:
                response.headers["Cache-Control"] = cache_control
                response.headers["ETag"] = etag

        if vary:
            response.headers["Vary"] = vary
        return response
    finally:
        flowdata.close()

def _uses(pipeline, key):

    # Whether the key is evidence one of the pipeline's elements accepts. The
    # web request itself, which the usage sharing element reads, is evidence
    # no element uses, whatever the filters accept.
    if key.lower() == "server.http-request":
        return False
    if key.startswith("header.") and \
            key[len("header."):] in _REVALIDATION_HEADERS:
        return False
    return any(
        element.filter_evidence_key(key)
        for element in pipeline.flow_elements)

def _opaque_tag(pipeline, evidence):

    # SHA-256 rather than hash(), which Python seeds afresh in each process,
    # so a browser revalidating against another process, after a restart or
    # behind a load balancer, still matches.
    digest = hashlib.sha256()
    for key in sorted(evidence):
        if _uses(pipeline, key):
            digest.update(key.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(evidence[key]).encode("utf-8"))
            digest.update(b"\0")
    return digest.hexdigest()[:32]

def _if_none_match_matches(if_none_match, opaque_tag):

    # RFC 9110 section 13.1.2. "*" matches, as there is always a response.
    # A list of entity tags matches when one of them has the same opaque
    # tag, whether or not either is weak. Anything else matches nothing.
    if if_none_match is None:
        return False
    value = if_none_match.strip(_OWS)
    if value == "*":
        return True
    tags = _entity_tags(value)
    return tags is not None and opaque_tag in tags

def _entity_tags(value):

    # The opaque tags of a list of entity tags, which may have whitespace
    # around its commas and empty elements (RFC 9110 section 5.6.1.2), or
    # None when the value is not such a list.
    tags = []
    position = 0
    while True:
        while position < len(value) and value[position] in _OWS:
            position += 1
        if position == len(value):
            return tags
        if value[position] != ",":
            tag = _ENTITY_TAG.match(value, position)
            if tag is None:
                return None
            tags.append(tag.group(2))
            position = tag.end()
            while position < len(value) and value[position] in _OWS:
                position += 1
            if position == len(value):
                return tags
            if value[position] != ",":
                return None
        position += 1

def _vary(pipeline, request):

    names = {}
    for name, _ in request.headers:
        key = name.lower()
        if key not in names and _uses(pipeline, "header." + key):
            names[key] = name
    return ", ".join(sorted(names.values(), key=str.lower))