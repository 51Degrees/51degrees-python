/* *********************************************************************
 * This Original Work is copyright of 51 Degrees Mobile Experts Limited.
 * Copyright 2019 51 Degrees Mobile Experts Limited, 5 Charlotte Close,
 * Caversham, Reading, Berkshire, United Kingdom RG4 7BY.
 *
 * This Original Work is licensed under the European Union Public Licence (EUPL) 
 * v.1.2 and is subject to its terms as set out below.
 *
 * If a copy of the EUPL was not distributed with this file, You can obtain
 * one at https://opensource.org/licenses/EUPL-1.2.
 *
 * The 'Compatible Licences' set out in the Appendix to the EUPL (as may be
 * amended by the European Commission) shall be deemed incompatible for
 * the purposes of the Work and the provisions of the compatibility
 * clause in Article 5 of the EUPL shall not apply.
 * 
 * If using the Work as, or as part of, a network application, by 
 * including the attribution notice(s) required under Article 5 of the EUPL
 * in the end user terms of the application under an appropriate heading, 
 * such notice(s) shall fulfill the requirements of that article.
 * ********************************************************************* */

%include <pybuffer.i>
%pybuffer_binary(unsigned char data[], long length);
%rename(refreshDataFromFile) refreshData(const char *fileName);
%rename(refreshDataFromMemory) refreshData(unsigned char data[], long length);

/* A refresh lets go of the Python global interpreter lock while the native
 * code loads the new data, so other threads go on processing Flow Data.
 * Refreshes still run one at a time, so that only one new copy of the data
 * is loaded at once beside the one in use. Each refreshData overload is
 * called through refreshWithoutGil. */
%{
#include <mutex>

/* Held for each refresh, so that two never run at once. */
static std::mutex oneRefreshAtATime;

/* Calls refresh without the global interpreter lock, and takes the lock back
 * before an error from the refresh is raised in Python. */
template <typename Refresh>
static void refreshWithoutGil(Refresh refresh) {
	PyThreadState *state = PyEval_SaveThread();
	try {
		std::lock_guard<std::mutex> lock(oneRefreshAtATime);
		refresh();
	}
	catch (...) {
		PyEval_RestoreThread(state);
		throw;
	}
	PyEval_RestoreThread(state);
}
%}

%feature("action") refreshData() %{
	refreshWithoutGil([&]() { arg1->refreshData(); });
%}
%feature("action") refreshData(const char *fileName) %{
	refreshWithoutGil([&]() { arg1->refreshData((char const *)arg2); });
%}
%feature("action") refreshData(unsigned char data[], long length) %{
	refreshWithoutGil([&]() { arg1->refreshData(arg2, arg3); });
%}

%include "cxx/src/dd/hash/hash.i"