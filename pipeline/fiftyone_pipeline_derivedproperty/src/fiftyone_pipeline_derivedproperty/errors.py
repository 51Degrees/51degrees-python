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


class ScriptValidationError(Exception):
    """!
    Raised when one or more scripts do not validate. The message lists
    every fault in every script, one per line, so one failure says
    everything that has to be fixed.
    """

    def __init__(self, faults):
        """!
        @param faults: every fault, each a validate.Fault.
        """
        from .validate import faults_message
        super().__init__("The derived property scripts are not valid.\n" +
                         faults_message(faults))
        self.faults = faults


class PipelineConfigurationError(Exception):
    """!
    Raised when a pipeline cannot supply what the scripts of a derived
    property element read, or when two elements write one derived
    property.
    """

    def __init__(self, faults):
        """!
        @param faults: one sentence for each problem.
        """
        super().__init__("The derived property element cannot be used in "
                         "this pipeline.\n" + "\n".join(faults))
        self.faults = faults
