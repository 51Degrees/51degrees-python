/* *********************************************************************
 * This Original Work is copyright of 51 Degrees Mobile Experts Limited.
 * Copyright 2026 51 Degrees Mobile Experts Limited, Davidson House,
 * Forbury Square, Reading, Berkshire, United Kingdom RG1 3EU.
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

/* Every compiler warning is on in the wrapper, so SWIG is asked not to turn
 * off any of its own. SWIG's runtime defines helper functions that a module
 * may not call. GCC and Clang are told so by SWIG's unused attribute, which
 * MSVC has no equivalent for, so on MSVC they are inline, as unused inline
 * functions are expected. The overloads are told apart by the arguments that
 * differ only (fast dispatch), which also keeps each check in a scope of its
 * own so no local hides another. */
%begin %{
#define SWIG_MSC_UNSUPPRESS_4505
#define SWIG_NO_CRT_SECURE_NO_DEPRECATE
#define SWIG_NO_SCL_SECURE_NO_DEPRECATE
#if defined(_MSC_VER)
#define SWIGINTERN static inline
#define SWIGINTERNINLINE static inline
#define SWIGRUNTIMEINLINE static inline
#endif
%}
%feature("fastdispatch");

%include <pybuffer.i>
%pybuffer_binary(unsigned char data[], long length);
%pybuffer_mutable_binary(unsigned char copy[], uint32_t size);
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

%include "cxx/src/ipi/ipi.i"
