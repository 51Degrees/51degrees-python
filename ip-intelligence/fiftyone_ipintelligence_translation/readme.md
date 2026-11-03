# IP Intelligence Country Translation

![51Degrees](https://51degrees.com/img/logo.png?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_translation-readme.md&utm_term=ip-intelligence-country-translation "Data rewards the curious") **Python IP Intelligence Country Translation**

[Developer Documentation](https://51degrees.com/documentation/index.html?utm_source=github&utm_medium=readme&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_translation-readme.md&utm_term=ip-intelligence-country-translation "Developer Documentation")

## Introduction

This package adds two flow elements that build on the on-premise 51Degrees IP
Intelligence engine.

On-premise IP Intelligence returns country information as weighted lists of ISO
country codes. These engines turn those codes into localized country names and
produce complete ordered lists, so an application can render a dropdown of
countries with the most probable country at the top.

* `CountryCodeTranslationEngine` translates the weighted country codes into
  English country names.
* `CountriesTranslationEngine` translates the English names into the browser
  language (resolved from the request evidence) and builds complete ordered
  "All" lists of every known country, most probable first.

These properties are only produced for the on-premise path. The cloud service
already returns them in their final form.

## Requirements

* Python 3.8+

## This package fiftyone_ipintelligence_translation

Built on top of:

* [fiftyone_pipeline_core](https://pypi.org/project/fiftyone-pipeline-core/)
* [fiftyone_pipeline_translation](https://pypi.org/project/fiftyone-pipeline-translation/)
