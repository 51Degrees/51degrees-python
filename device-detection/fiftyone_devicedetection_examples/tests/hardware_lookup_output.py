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

"""How a test reads what the TAC and native model lookup examples print.
The live tests in test_cloudexamples.py use it, and
test_hardware_lookup_output.py tests it without a key.
"""

# What the TAC and native model examples print in place of their lookups
# when the resource key does not carry the hardware lookup.
NO_HARDWARE_LOOKUP = "does not include HardwarePlatform.Profiles"

# What ExampleUtils.get_human_readable gives for a property with no value,
# alone or followed by the reason in parentheses.
NO_VALUE = "Unknown"


def is_value(text):
    """Whether the text is a value rather than empty or the rendering of a
    property with no value."""
    return (text != "" and text != NO_VALUE
            and not text.startswith(NO_VALUE + " ("))


def vendor_and_model(line):
    """The vendor and model of a device line, which has the form
    '<vendor> <name> (<model>)', or None when the line has another form.
    The vendor is the text before the first space, and the model the text
    inside the final parentheses, which may hold parentheses of their own
    when it has no value and gives the reason."""
    text = line.strip()
    if not text.endswith(")"):
        return None
    depth = 0
    for index in range(len(text) - 1, -1, -1):
        if text[index] == ")":
            depth += 1
        elif text[index] == "(":
            depth -= 1
            if depth == 0:
                break
    else:
        return None
    before = text[:index].strip()
    if before == "":
        return None
    return before.split(" ", 1)[0], text[index + 1:-1].strip()


def lines_under(output, heading):
    """The tab-indented lines printed straight after the heading, or None
    when the heading was not printed."""
    lines = output.split("\n")
    if heading not in lines:
        return None
    under = []
    for line in lines[lines.index(heading) + 1:]:
        if not line.startswith("\t"):
            break
        under.append(line)
    return under


def lookup_fault(output, lookup, kind, values):
    """What is wrong with the output of the TAC or native model example, or
    None when it lists, for each value it looked up, at least one device
    with a vendor and a model. lookup names the lookup for the message when
    the resource key does not carry it, and kind names what each value is,
    as the example's heading does."""
    if NO_HARDWARE_LOOKUP in output:
        return ("The resource key in _51DEGREES_RESOURCE_KEY_BESPOKE does "
                "not include HardwarePlatform.Profiles, which the "
                f"{lookup} needs.")

    for value in values:
        heading = f"Which devices are associated with the {kind} '{value}'?"
        devices = [vendor_and_model(line)
                   for line in lines_under(output, heading) or []]
        if not any(device and is_value(device[0]) and is_value(device[1])
                   for device in devices):
            return ("No device with a vendor and a model was listed for the "
                    f"{kind} '{value}'.")

    return None
