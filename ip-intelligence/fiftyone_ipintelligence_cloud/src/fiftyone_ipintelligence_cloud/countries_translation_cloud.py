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

"""!
The cloud engine for country names translated into the browser's language.
"""

from .weighted_cloud_engine import WeightedCloudEngine


class CountriesTranslationCloud(WeightedCloudEngine):
    """!
    Reads the "countrynamestranslated" section of the cloud response into
    flowdata.countrynamestranslated. That is the data key of the on-premise
    CountriesTranslationEngine in fiftyone_ipintelligence_translation, and
    the properties have the same names, so code that reads the results works
    with either. A CloudRequestEngine has to come earlier in the pipeline,
    and the key in use has to carry the translated country names.

    Each weighted list, such as CountryNamesGeographicalTranslated, gives
    each name with its weighting from 0.0 to 1.0. The lists whose names end
    in "All" are aligned by position, so the country code at a position in
    CountryCodesGeographicalAll names the same country as the entry at that
    position in CountryNamesGeographicalAllTranslated, and the same holds
    for CountryCodesPopulationAll and CountryNamesPopulationAllTranslated.
    """

    DATA_KEY = "countrynamestranslated"

    def __init__(self):

        super(CountriesTranslationCloud, self).__init__()

        self.datakey = self.DATA_KEY
