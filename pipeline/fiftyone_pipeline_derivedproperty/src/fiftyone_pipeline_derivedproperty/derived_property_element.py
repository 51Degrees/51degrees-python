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

from fiftyone_pipeline_core.aspectproperty_value import AspectPropertyValue
from fiftyone_pipeline_core.flowelement import FlowElement

from .canonical import canonical
from .derived_property_data import DerivedPropertyData
from .errors import PipelineConfigurationError, ScriptValidationError
from .evaluate import NoValue, evaluate
from .jsvalues import is_number
from .script_set import ScriptSet
from .validate import Fault

## The element data key every derived property element writes under.
DATA_KEY = "derived"

_NOT_PRESENT = "property not present on this request"

# The settings the element takes, matched without regard to case or
# underscores, so that Scripts and ScriptFiles, as the other languages
# write them, work too.
_SETTINGS = {"scripts": "scripts", "scriptfiles": "script_files"}

# The Output fields given in each property's metadata beyond the name,
# type, category and description every element gives.
_OUTPUT_METADATA = [
    ("StoredValueType", "storedvaluetype"),
    ("DefaultValue", "defaultvalue"),
    ("IsList", "islist"),
    ("IsMandatory", "ismandatory"),
    ("IsObsolete", "isobsolete"),
    ("IsPopular", "ispopular"),
    ("ExportValues", "exportvalues"),
    ("Url", "url"),
    ("DisplayOrder", "displayorder"),
    ("PropertyId", "propertyid"),
    ("VendorIds", "vendorids"),
    ("Dependencies", "dependencies"),
    ("Values", "values")
]

# What a read gives where the request carried no element data at all.
_NO_ELEMENT_DATA = object()


class DerivedPropertyElement(FlowElement):
    """!
    Computes new properties from properties other elements have already
    put into the flow data, following one or more scripts in the format of
    the derived-properties repository. Every script writes one property
    under the element data key derived.

    The element holds no data file, sends no request and reads no
    evidence, so it accepts no evidence.
    """

    def __init__(self, compiled=None, **settings):
        """!
        Builds the element from its settings, as a pipeline configuration
        file gives them, and from scripts a builder has already read.

        @param compiled: scripts read by DerivedPropertyElementBuilder.
        @param settings: scripts names scripts built into this package and
            script_files gives paths to script files, where a file name may
            hold a wildcard. Each is a list of strings, or one string with
            commas between the entries, where an entry holding a comma is
            wrapped in double quotes. The names are matched without regard
            to case or underscores, and any other setting is refused.
        @raise ScriptValidationError: where a script does not validate, or
            two scripts write one property.
        """
        super().__init__()
        self.datakey = DATA_KEY
        script_set = ScriptSet()
        _read_settings(settings, script_set)
        self.scripts = script_set.compile() + list(compiled or [])
        if not self.scripts:
            raise ValueError(
                "At least one script must be configured. Name the scripts "
                "built into this package with the scripts setting, give "
                "script files with script_files, or use "
                "DerivedPropertyElementBuilder.")
        _check_output_names_are_unique(self.scripts)

        ## The metadata of the properties this element writes, being the
        # Output block of each script, by lower case name.
        self.script_properties = {}
        for script in self.scripts:
            self.script_properties[script.output["Name"].lower()] = \
                _metadata(script)
        self.properties = dict(self.script_properties)

        # The scripts that have reported a missing element data, as that
        # is reported once rather than on every request.
        self._reported = set()

    def get_properties(self):
        """!
        The properties written under derived, being those of every derived
        property element in the pipelines this one is in. They all write
        one element data, so each element gives them all.
        """
        properties = {}
        for pipeline in self.pipelines:
            for element in pipeline.flow_elements:
                if element is not self and _is_derived_element(element):
                    properties.update(element.script_properties)
        properties.update(self.script_properties)
        return properties

    def on_registration(self, pipeline):
        """!
        Refuses a pipeline that cannot supply a property a script reads,
        or in which another element writes a property a script writes,
        then logs what each script produces.

        @raise PipelineConfigurationError: where the pipeline cannot be
            used.
        """
        self._check_pipeline(pipeline)
        self._log_scripts(pipeline)

    def process_internal(self, flowdata):
        """!
        Runs every script in order, so a script can read what an earlier
        one wrote.
        """
        # Every derived property element in a pipeline writes one element
        # data, as the properties of all of them are under derived.
        data = flowdata.data.get(DATA_KEY)
        if not isinstance(data, DerivedPropertyData):
            data = DerivedPropertyData(self)
            flowdata.set_element_data(data)
        for index, script in enumerate(self.scripts):
            properties = {}
            for prop in script.properties:
                value = self._read_source(flowdata, script, index, prop)
                if value is not _NO_ELEMENT_DATA:
                    properties[prop.name] = value
            result = evaluate(script, properties)
            data.set_value(
                script.output["Name"],
                AspectPropertyValue(None, result.value) if result.has_value
                else AspectPropertyValue(result.message))

    # -------------------------------------------------------------------
    # Reading source properties.
    # -------------------------------------------------------------------

    def _read_source(self, flowdata, script, index, prop):
        """!
        Reads one source property for one request, in the form the
        evaluator takes. A value with no value of its own becomes a
        NoValue, and a weighted list becomes a list of { Value, Weight }.
        """
        dot = prop.name.index(".")
        key = prop.name[:dot]
        name = prop.name[dot + 1:]

        element_data = flowdata.data.get(key.lower())
        if element_data is None:
            self._report_missing_element_data(flowdata, script, index, prop,
                                              key)
            return _NO_ELEMENT_DATA

        try:
            raw = element_data.get(name)
        except Exception as error:
            # An element that does not have the property says why, and
            # that reason is carried.
            return NoValue(str(error) or _NOT_PRESENT)

        # A source value with its own no value state hands its message
        # on, so the reason reaches back to the element that knows it.
        if _is_aspect_property_value(raw):
            if not raw.has_value():
                return NoValue(raw.no_value_message() or _NOT_PRESENT)
            raw = raw.value()
        if isinstance(raw, list):
            return _weighted(raw)
        return raw

    def _report_missing_element_data(self, flowdata, script, index, prop,
                                     key):
        """!
        Reports, once for each script, that a request carried no element
        data at all under a key the pipeline has an element for, which
        means that element ran after this one.
        """
        if index in self._reported:
            return
        self._reported.add(index)
        flowdata.pipeline.log(
            "error",
            "The script '" + script.name + "' reads '" + prop.name + "', "
            "and the request carried no element data '" + key + "' at all, "
            "so the script has no value. The usual cause is the element "
            "that supplies it running after this element rather than "
            "before it. This is reported once.")

    # -------------------------------------------------------------------
    # Building the pipeline.
    # -------------------------------------------------------------------

    def _log_scripts(self, pipeline):
        """!
        Logs one line for each script at information level, a warning for
        a deprecated one, and the compiled script as canonical JSON at
        debug level.
        """
        for script in self.scripts:
            pipeline.log(
                "info",
                "Derived property script '" + script.name + "' version " +
                script.version + ", format " + str(script.format) +
                ", from " + script.source + ", produces '" + DATA_KEY +
                "." + script.output["Name"] + "' as " +
                script.output["ValueType"] + ".")
            if script.deprecated:
                pipeline.log(
                    "warning",
                    "Derived property script '" + script.name +
                    "' is deprecated. " + script.deprecation_note)
            pipeline.log(
                "debug",
                "Derived property script '" + script.name +
                "' compiled to " + canonical(script))

    def _check_pipeline(self, pipeline):
        """!
        The checks run when the pipeline adds the element. Where an
        element sits is not judged, because the element may read a
        property from an element added after it on purpose.
        """
        others = [e for e in pipeline.flow_elements if e is not self]
        faults = []

        for script in self.scripts:
            output_name = script.output["Name"]
            if any(_same_key(e.datakey, DATA_KEY) and
                   _supplies(e, output_name) is True for e in others):
                faults.append(
                    "The script '" + script.name + "' writes the derived "
                    "property '" + output_name + "', and another element "
                    "in the pipeline already writes a property of that "
                    "name. One pipeline writes each derived property once.")

        for index, script in enumerate(self.scripts):
            for prop in script.properties:
                if self._is_supplied(others, prop, index):
                    continue
                # Every property a script names is needed, so a pipeline
                # that cannot supply one would give no value on every
                # request.
                faults.append(
                    "The script '" + script.name + "' needs the property '" +
                    prop.name + "', and no element in the pipeline supplies "
                    "it. Either add the element that supplies '" +
                    prop.name + "', or change the script so that it does "
                    "not name '" + prop.name + "'.")

        if faults:
            raise PipelineConfigurationError(faults)

    def _is_supplied(self, others, prop, index):
        dot = prop.name.index(".")
        key = prop.name[:dot]
        name = prop.name[dot + 1:]
        # A script can read what an earlier script of this element
        # writes, and nothing that a later one writes, as the scripts run
        # in order.
        if _same_key(key, DATA_KEY):
            for earlier in self.scripts[:index]:
                if _same_key(earlier.output["Name"], name):
                    return True
        return any(_same_key(e.datakey, key) and _supplies(e, name)
                   is not False for e in others)


# ---------------------------------------------------------------------
# Settings and metadata.
# ---------------------------------------------------------------------

def _read_settings(settings, script_set):
    for key, value in settings.items():
        setting = _SETTINGS.get(key.replace("_", "").lower())
        if setting is None:
            # A setting written wrongly would otherwise leave its scripts
            # out without a word.
            raise ValueError(
                "The derived property element has no setting '" + key +
                "'. Its settings are scripts and script_files.")
        for entry in _list_setting(setting, value):
            if setting == "scripts":
                script_set.add_built_in(entry)
            else:
                script_set.add_files(entry)


def _list_setting(name, value):
    if value is None:
        return []
    if isinstance(value, str):
        return [] if value.strip() == "" else _split(value)
    if (isinstance(value, (list, tuple)) and
            all(isinstance(entry, str) for entry in value)):
        return list(value)
    raise TypeError(
        "The " + name + " setting must be a list of strings, or one string "
        "with commas between the entries.")


def _split(value):
    """!
    Splits a setting on its commas, where an entry wrapped in double
    quotes may hold a comma, and two double quotes inside the quotes are
    one.
    """
    entries = []
    current = ""
    quoted = False
    i = 0
    while i < len(value):
        character = value[i]
        if character == '"':
            if quoted and i + 1 < len(value) and value[i + 1] == '"':
                current += '"'
                i += 1
            else:
                quoted = not quoted
        elif character == "," and not quoted:
            entries.append(current.strip())
            current = ""
        else:
            current += character
        i += 1
    entries.append(current.strip())
    return entries


def _check_output_names_are_unique(scripts):
    seen = {}
    faults = []
    for script in scripts:
        key = script.output["Name"].lower()
        if key in seen:
            faults.append(Fault(
                script.name, script.source, "Output.Name", None,
                "two scripts in the same element write the property '" +
                script.output["Name"] + "', being '" + seen[key] + "' and '" +
                script.name + "'. One element writes each property once"))
            continue
        seen[key] = script.name
    if faults:
        raise ScriptValidationError(faults)


def _metadata(script):
    """!
    The metadata of the property a script writes, with the keys the other
    elements give followed by the rest of the Output block.
    """
    output = script.output
    result = {
        "name": output["Name"],
        "type": output["ValueType"],
        "category": output.get("Category") or "",
        "description": output.get("Description")
    }
    for field, key in _OUTPUT_METADATA:
        if output.get(field) is not None:
            result[key] = output[field]
    return result


# ---------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------

def _is_derived_element(element):
    return (_same_key(getattr(element, "datakey", None), DATA_KEY) and
            isinstance(getattr(element, "script_properties", None), dict))


def _same_key(a, b):
    return (isinstance(a, str) and isinstance(b, str) and
            a.lower() == b.lower())


def _supplies(element, name):
    """!
    Whether an element gives a property, or None where it does not know
    yet. A cloud engine learns its properties from the cloud service, so
    an element listing no properties may give any property under its key.
    """
    try:
        # Another derived property element is asked only for what it
        # writes itself.
        properties = (element.script_properties
                      if _is_derived_element(element)
                      else element.get_properties())
    except Exception:
        return None
    if not isinstance(properties, dict) or not properties:
        return None
    for key, meta in properties.items():
        if _same_key(key, name):
            return True
        if isinstance(meta, dict) and _same_key(meta.get("name"), name):
            return True
    return False


def _is_aspect_property_value(value):
    return isinstance(value, AspectPropertyValue) or (
        callable(getattr(value, "has_value", None)) and
        callable(getattr(value, "value", None)) and
        callable(getattr(value, "no_value_message", None)))


def _weighted(items):
    """!
    A list as the evaluator takes it. A list of weighted values, whose
    members each carry a value and a weight as 51Degrees elements give
    them, becomes a list of { Value, Weight }, using the raw weighting
    where there is one. Any other list is left as it is, which the
    evaluator refuses where a single value is needed.
    """
    members = []
    for item in items:
        if not isinstance(item, dict):
            return items
        fields = {str(k).lower(): v for k, v in item.items()}
        if "value" not in fields:
            return items
        weight = 0
        for field in ("rawweighting", "weighting", "weight"):
            if is_number(fields.get(field)):
                weight = fields[field]
                break
        members.append({"Value": fields["value"], "Weight": weight})
    return members if members else items
