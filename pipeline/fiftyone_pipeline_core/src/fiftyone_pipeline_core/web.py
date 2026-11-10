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

from types import MappingProxyType

from flask import has_request_context, request, session

from .evidence import HTTP_REQUEST_KEY

def request_line_path(request):

    """!
    The path of the request line as the server received it, when the server
    says what that was, and otherwise the path Flask decoded.
    """

    raw = request.environ.get("RAW_URI") or request.environ.get("REQUEST_URI")
    if raw:
        return raw.split("?", 1)[0].split("#", 1)[0]
    return request.path

def webevidence(request):

    """!
    Get evidence from a web request (gets headers, cookies, session values,
    query parameters and the fields of a posted form, and the request itself
    as server.http-request)
    
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

    # Values stored in the session. They are read without marking the session
    # as accessed, which would add a Vary: Cookie header to the response, and
    # only plain values are taken. Numbers and booleans are added as text,
    # because the on-premise engines take evidence values as text only.
    if has_request_context():
        for name, value in dict.items(session._get_current_object()):
            if isinstance(value, (str, int, float, bool)):
                webevidence["session." + name] = str(value)

    webevidence["server.client-ip"] =  request.remote_addr

    webevidence["server.host-ip"] =  request.host

    if (request.is_secure):
        webevidence["header.protocol"] = "https"
    else:
        webevidence["header.protocol"] = "http"

    # The request itself, for the usage sharing element, which accepts no
    # evidence and shares what it finds. A read-only view of the parts above
    # and the method and path of the request line, keyed as evidence is. It
    # leaves out the Cookie header, which cookies already cover. Evidence
    # keeps it from every other element.
    view = {key: value for key, value in webevidence.items()
            if key not in ("header.cookie", "server.host-ip")}
    view["server.request-method"] = request.method
    view["server.request-path"] = request_line_path(request)
    webevidence[HTTP_REQUEST_KEY] = MappingProxyType(view)

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