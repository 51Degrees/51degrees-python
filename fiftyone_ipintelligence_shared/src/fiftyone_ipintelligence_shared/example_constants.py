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

# Example IP addresses to use as evidence. The cloud engine expects the
# address under "query.client-ip-51d", the on-premise engine accepts
# "query.client-ip" or "server.client-ip" (and other parseable evidence).
# These values mirror the .NET examples' ExampleUtils.EvidenceValues.
EVIDENCE_VALUES = [
        # An IPv4 address.
        { "query.client-ip": "116.154.188.222" },
        # An IPv4 address.
        { "query.client-ip": "1.3.32.31" },
        # An IPv4 address.
        { "query.client-ip": "45.236.48.61" },
        # An IPv6 address.
        { "query.client-ip": "2001:0db8:085a:0000:0000:8a2e:0370:7334" },
    ]

# Note: the .NET examples' Constants.cs still uses the legacy name
# "51Degrees-EnterpriseIpiV41.ipi", but the published enterprise/ASN data
# files use the "IPIV4" infix (cf. 51Degrees-IPIV4AsnIpiV41.ipi in the
# ip-intelligence-data repo), so the current name is used here.
ENTERPRISE_DATAFILE_NAME = '51Degrees-IPIV4EnterpriseIpiV41.ipi'
LITE_DATAFILE_NAME = '51Degrees-LiteIpiV41.ipi'
# The ASN data file is the freely available data file committed
# to the ip-intelligence-data submodule. It only contains the network
# (ASN) properties, but is useful for testing the on-premise engine against
# the current data format without an enterprise data file.
ASN_DATAFILE_NAME = '51Degrees-IPIV4AsnIpiV41.ipi'
EVIDENCE_FILE_NAME = 'evidence.yml'
