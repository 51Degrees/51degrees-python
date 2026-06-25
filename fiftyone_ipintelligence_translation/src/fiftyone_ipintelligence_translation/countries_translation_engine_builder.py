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

from .countries_translation_engine import CountriesTranslationEngine
from .resources import get_all_countries


class CountriesTranslationEngineBuilder:

    """!
    Builder for the CountriesTranslationEngine element. Loads the country code
    resource (countrycodes.en_GB.yml) which lists all known country codes and
    their English names. The country name translation resources (countries.*)
    are handled by the base translation engine.
    """

    def __init__(self, logger_factory=None):

        """!
        Constructor.

        @param logger_factory: Accepted for parity with the other SDKs; the
        Python pipeline performs logging through the pipeline the element is
        added to, so it is not required here.
        """

        self._logger_factory = logger_factory

    def build(self):

        """!
        Build a new instance of CountriesTranslationEngine.
        """

        return CountriesTranslationEngine(get_all_countries())
