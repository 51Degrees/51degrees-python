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

## @example derived_property.py
#
# This example adds the derived property element to a pipeline. The element
# works out new properties from properties that other elements in the
# pipeline have already given, following scripts written in YAML or JSON.
# It holds no data file, sends nothing over the network and needs no key.
#
# The scripts here read the width and height of a screen, which come from a
# small flow element in screen_element.py beside this example. In your own
# pipeline, the elements that give the properties your scripts read take
# the place of the screen element.
#
# You will learn:
#
# 1. How to give the element a script held in your code as text
# 2. How to give it a script read from a file
# 3. How to build the same pipeline from a configuration file
# 4. What a derived property holds when a property its script reads is
#    missing from the request
#
# Each derived property is an AspectPropertyValue. When every property its
# script reads is there, has_value() is True and value() gives the value.
# When any one is missing, has_value() is False and no_value_message()
# names each property that was missing and why, rather than giving a value
# worked out from part of what the script needs.
#
# The scripts built into the package are added by name with
# add_built_in_script, and builtin_script_names() lists them. This example
# uses none of them, so it runs the same whether or not they are there.
#
# This example is available in full on [GitHub](https://github.com/51Degrees/51degrees-python/blob/main/pipeline/fiftyone_pipeline_derivedproperty/examples/derived_property.py).
#
# It needs no data file, no key and no network. Run it from any folder,
# once fiftyone_pipeline_core and fiftyone_pipeline_derivedproperty are
# installed, for example from the pipeline folder with
# ```
# python fiftyone_pipeline_derivedproperty/examples/derived_property.py
# ```
#
# Expected output, before the Find out more section:
# ```
# 1. A script held in this example as text
#
#    Width  Height  ScreenSize
#    1920   1080    Large
#    1024   768     Medium
#    390    844     Small
#
# 2. A script read from IsFullHd.yaml beside this example
#
#    Width  Height  IsFullHd
#    1920   1080    True
#    1024   768     False
#    390    844     False
#
# 3. The same pipeline as 2, built from derived_property.json
#
#    Width  Height  IsFullHd
#    1920   1080    True
#    1024   768     False
#    390    844     False
#
# 4. A request that gives no screen height
#
#    The request gives a width of 1920 and no height.
#    ScreenSize has_value() is False, and no_value_message() gives the reason.
#
#    Derived property 'ScreenSize' has no value because 1 source property was not
#    available. 'screen.Height' (element 'screen' has no value for 'Height':
#    property not present on this request). Usual causes are the element that
#    supplies the property not being in the pipeline, or being added after this
#    element rather than before it, the property being excluded in the engine
#    configuration, the property not being included in the resource key, or
#    JavaScript that populates the property not having run yet.
# ```

import json
import os
import textwrap

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_derivedproperty import DerivedPropertyElementBuilder

# The flow element giving the screen's width and height, from
# screen_element.py beside this example. Python finds screen_element.py
# because, when running a file, Python looks first in that file's folder.
from screen_element import SCREEN_HEIGHT, SCREEN_WIDTH, ScreenElement

# Where to go next, printed when the example ends.
FIND_OUT_MORE = [
    ("Pipeline API documentation",
     "https://51degrees.com/documentation/_pipeline_api__concepts__pipeline_basics.html?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_derivedproperty-examples-derived_property.py&utm_term=find-out-more-documentation"),
    ("Build your own",
     "https://51degrees.com/build-your-own?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_derivedproperty-examples-derived_property.py&utm_term=find-out-more-build-your-own"),
    ("Contact us",
     "https://51degrees.com/contact-us?utm_source=code&utm_medium=example&utm_campaign=51degrees-python&utm_content=fiftyone_pipeline_derivedproperty-examples-derived_property.py&utm_term=find-out-more-contact"),
    ("Derived property scripts and their format",
     "https://github.com/51Degrees/derived-properties"),
    ("Pipeline API for Python",
     "https://github.com/51Degrees/51degrees-python/tree/main/pipeline"),
    ("Pipeline API specification",
     "https://github.com/51Degrees/specifications/tree/main/pipeline-specification"),
]

# The folder holding this example, its script file and its configuration
# file.
EXAMPLE_FOLDER = os.path.dirname(os.path.abspath(__file__))

# The script file beside this example.
SCRIPT_FILE = os.path.join(EXAMPLE_FOLDER, "IsFullHd.yaml")

# The configuration file beside this example, which builds the same
# pipeline as pipeline_from_file.
CONFIGURATION_FILE = os.path.join(EXAMPLE_FOLDER, "derived_property.json")

# A script held in this example as text, which writes the property
# ScreenSize from the screen's width and height. Rules are read in order,
# and the first whose When is true gives the value. Every script ends with
# an Else, which gives the value when no other rule does.
SCREEN_SIZE_SCRIPT = """
Format: 1
Name: ScreenSize
Version: 1.0.0
Output:
  Name: ScreenSize
  Description: The size of the screen, being Large, Medium or Small.
  ValueType: string
  IsList: false
  Category: Example
Rules:
  - When:
      All:
        - { Property: screen.Width, Ge: 1280 }
        - { Property: screen.Height, Ge: 720 }
    Then: Large
  - When: { Property: screen.Width, Ge: 768 }
    Then: Medium
  - Else: Small
"""

# The screens each pipeline is given, as a width and a height in pixels.
SCREENS = [(1920, 1080), (1024, 768), (390, 844)]

# The width of a screen whose height the request does not give.
WIDTH_WITHOUT_HEIGHT = 1920

# A console has no page, so leave out the elements that write the
# client-side script and set response headers.
SETTINGS = {
    "add_javascript_builder": False,
    "use_setheader_properties": False,
}

# How each line printed under a heading starts, and each row of a table.
INDENT = "   "
ROW = INDENT + "{:<7}{:<8}{}"


def pipeline_from_text():

    """!
    A pipeline whose derived property element runs the script held in this
    example as text.
    """

    derived = (DerivedPropertyElementBuilder()
               # The name given here must equal the script's own Name.
               .add_script("ScreenSize", SCREEN_SIZE_SCRIPT)
               .build())

    # Elements run in the order they are added, so the derived property
    # element goes after the elements giving the properties it reads.
    return PipelineBuilder(SETTINGS).add(ScreenElement()).add(derived).build()


def pipeline_from_file():

    """!
    A pipeline whose derived property element runs the script in the file
    beside this example.
    """

    derived = (DerivedPropertyElementBuilder()
               # The file name without its extension must equal the
               # script's own Name. A wildcard in the file name, such as
               # scripts/*.yaml, adds every file it matches.
               .add_script_file(SCRIPT_FILE)
               .build())

    return PipelineBuilder(SETTINGS).add(ScreenElement()).add(derived).build()


def pipeline_from_configuration():

    """!
    The pipeline that pipeline_from_file builds, built instead from the
    configuration file beside this example. The file names each element by
    its module and class, and gives the derived property element the script
    file in its parameters.
    """

    with open(CONFIGURATION_FILE, encoding="utf-8") as file:
        configuration = json.load(file)

    # A relative path in script_files is read from the current folder, so
    # the pipeline is built from this example's folder, where the script
    # file is. The script is read while the pipeline is built, and the
    # current folder is then put back.
    current = os.getcwd()
    os.chdir(EXAMPLE_FOLDER)
    try:
        return PipelineBuilder().build_from_configuration(configuration)
    finally:
        os.chdir(current)


def value_of(pipeline, name, width, height=None):

    """!
    Process a request giving a screen's width, and its height when there is
    one, and return the derived property called name.
    """

    with pipeline.create_flowdata() as flowdata:
        # Evidence from a query string is text.
        flowdata.evidence.add(SCREEN_WIDTH, str(width))
        if height is not None:
            flowdata.evidence.add(SCREEN_HEIGHT, str(height))
        flowdata.process()

        # Every derived property element writes under the element data key
        # derived.
        return flowdata.derived.get(name)


def print_table(pipeline, name):

    """!
    Print the derived property called name for each screen, a row each.
    """

    print()
    print(ROW.format("Width", "Height", name))
    for width, height in SCREENS:
        value = value_of(pipeline, name, width, height)
        print(ROW.format(
            width, height, value.value() if value.has_value() else "none"))
    print()


def print_missing(pipeline):

    """!
    Print what ScreenSize holds for a request that gives no screen height.
    """

    value = value_of(pipeline, "ScreenSize", WIDTH_WITHOUT_HEIGHT)

    print()
    print(f"{INDENT}The request gives a width of {WIDTH_WITHOUT_HEIGHT} "
          "and no height.")
    # Reading value() here would raise an exception carrying the same
    # message, so check has_value() before reading a value.
    print(f"{INDENT}ScreenSize has_value() is {value.has_value()}, and "
          "no_value_message() gives the reason.")
    print()
    print(textwrap.fill(
        value.no_value_message(), width=79, initial_indent=INDENT,
        subsequent_indent=INDENT, break_on_hyphens=False))
    print()


def print_find_out_more():

    """!
    Print the "Find out more" section, a line of "=" and then each label
    with its link.
    """

    print("=" * 79)
    print("Find out more:")
    for label, url in FIND_OUT_MORE:
        print(f"\t{label}: {url}")


def main():

    print("1. A script held in this example as text")
    with pipeline_from_text() as pipeline:
        print_table(pipeline, "ScreenSize")

    print(f"2. A script read from {os.path.basename(SCRIPT_FILE)} beside "
          "this example")
    with pipeline_from_file() as pipeline:
        print_table(pipeline, "IsFullHd")

    print("3. The same pipeline as 2, built from "
          f"{os.path.basename(CONFIGURATION_FILE)}")
    with pipeline_from_configuration() as pipeline:
        print_table(pipeline, "IsFullHd")

    print("4. A request that gives no screen height")
    with pipeline_from_text() as pipeline:
        print_missing(pipeline)

    print_find_out_more()


if __name__ == "__main__":
    main()
