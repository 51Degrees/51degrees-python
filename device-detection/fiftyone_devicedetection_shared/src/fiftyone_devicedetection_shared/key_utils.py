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

import os
import warnings


class KeyUtils:
	# The upper case names already reported as deprecated, so each is
	# reported once.
	_reported_upper_case = set()

	# A key from the environment variable of that name. When that variable
	# is unset or empty, the variable with the same name in upper case is
	# read, which is deprecated and reported once with a FutureWarning.
	@staticmethod
	def get_named_key(key_name):
		value = os.environ.get(key_name)
		upper = key_name.upper()
		if value or upper == key_name:
			return value
		upper_value = os.environ.get(upper)
		if not upper_value:
			return value or upper_value
		if upper not in KeyUtils._reported_upper_case:
			KeyUtils._reported_upper_case.add(upper)
			warnings.warn(
				"Reading a key from the upper case form of its variable name "
				"is deprecated. The key was read from {0} because {1} is not "
				"set, so set {1} to the same value.".format(upper, key_name),
				FutureWarning, stacklevel=2)
		return upper_value
