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

from fiftyone_pipeline_translation.translation_engine_base import (
    TranslationEngineBase)
from fiftyone_pipeline_translation.missing_translation_behavior import (
    MissingTranslationBehavior)

from .constants import Constants
from .resources import get_country_code_resources


class CountryCodeTranslationEngine(TranslationEngineBase):

    """!
    Engine which takes the weighted country code properties from the IP
    Intelligence engine and translates them to country names. The country names
    are always in English (the fixed en_GB resource). Results are stored under
    the Constants.COUNTRY_NAMES_KEY element data key.

    All translation files are loaded as package resources, so no configuration
    is required.
    """

    def __init__(self):

        """!
        Constructor.
        """

        super().__init__(
            # Source element data key of the IP Intelligence engine.
            "ip",
            [
                ("CountryCodesGeographical", "CountryNamesGeographical"),
                ("CountryCodesPopulation", "CountryNamesPopulation"),
            ],
            get_country_code_resources(),
            "en_GB",
            MissingTranslationBehavior.ORIGINAL)

        self.datakey = Constants.COUNTRY_NAMES_KEY
