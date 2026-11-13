# IP Intelligence Country Translation

![51Degrees](https://raw.githubusercontent.com/51Degrees/51degrees-python/main/.github/images/logo-160.png "Data rewards the curious") **Python IP Intelligence Country Translation**

[Developer Documentation](https://51degrees.com/documentation/_ip_intelligence__quickstart.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_translation&utm_term=ip-intelligence-country-translation "Developer Documentation")

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

## Find out more

- [IP Intelligence](https://51degrees.com/ip-intelligence?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_translation&utm_term=find-out-more-ip-intelligence)
- [IP Intelligence documentation](https://51degrees.com/documentation/index.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_translation&utm_term=find-out-more-documentation)
- [Getting started](https://51degrees.com/documentation/_ip_intelligence__quickstart.html?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_translation&utm_term=find-out-more-getting-started)
- [Pricing](https://51degrees.com/pricing?utm_source=pypi&utm_medium=package&utm_campaign=51degrees-python&utm_content=fiftyone_ipintelligence_translation&utm_term=find-out-more-pricing)
- https://github.com/51Degrees/51degrees-python
