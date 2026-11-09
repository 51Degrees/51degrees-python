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

from collections import deque
import threading

# The default number of failed sends within the failures window that
# pauses sending.
FAILURES_TO_ENTER_RECOVERY_DEFAULT = 10

# The range of failed sends that can be set to pause sending.
FAILURES_TO_ENTER_RECOVERY_MIN = 1
FAILURES_TO_ENTER_RECOVERY_MAX = 100

# The default time in seconds over which failed sends are counted.
FAILURES_WINDOW_SECONDS_DEFAULT = 100

# The default length in seconds of the first pause after failed sends.
INITIAL_RECOVERY_DELAY_SECONDS_DEFAULT = 2.0

# The default longest pause in seconds.
MAX_RECOVERY_DELAY_SECONDS_DEFAULT = 300.0

# The default multiplier applied to the pause each time the send tried
# when a pause ends fails.
RECOVERY_MULTIPLIER_DEFAULT = 2.0


class ShareUsageBackOff:
    """!
    Decides when usage sharing may send. Sending pauses for the initial
    delay once the set number of sends fail within the window. A failed
    send after a pause multiplies the delay, up to the maximum, and a
    successful send ends the back-off. Only sending pauses, so evidence is
    still queued while paused. Each method takes the time from the caller,
    in seconds.
    """

    def __init__(
        self,
        failures_to_enter_recovery = FAILURES_TO_ENTER_RECOVERY_DEFAULT,
        failures_window_seconds = FAILURES_WINDOW_SECONDS_DEFAULT,
        initial_recovery_delay_seconds = INITIAL_RECOVERY_DELAY_SECONDS_DEFAULT,
        max_recovery_delay_seconds = MAX_RECOVERY_DELAY_SECONDS_DEFAULT,
        recovery_multiplier = RECOVERY_MULTIPLIER_DEFAULT):

        if not (isinstance(failures_to_enter_recovery, int)
                and FAILURES_TO_ENTER_RECOVERY_MIN <= failures_to_enter_recovery
                <= FAILURES_TO_ENTER_RECOVERY_MAX):
            raise ValueError(
                "failures_to_enter_recovery must be from "
                f"{FAILURES_TO_ENTER_RECOVERY_MIN} to "
                f"{FAILURES_TO_ENTER_RECOVERY_MAX}. "
                f"Received: {failures_to_enter_recovery}.")
        if not failures_window_seconds >= 1:
            raise ValueError("failures_window_seconds must be 1 or more.")
        if not initial_recovery_delay_seconds > 0:
            raise ValueError(
                "initial_recovery_delay_seconds must be more than 0.")
        if not max_recovery_delay_seconds > 0:
            raise ValueError(
                "max_recovery_delay_seconds must be more than 0.")
        if not recovery_multiplier >= 1:
            raise ValueError("recovery_multiplier must be 1 or more.")

        self.failures_to_enter_recovery = failures_to_enter_recovery
        self.failures_window_seconds = failures_window_seconds
        self.initial_recovery_delay_seconds = initial_recovery_delay_seconds
        self.max_recovery_delay_seconds = max_recovery_delay_seconds
        self.recovery_multiplier = recovery_multiplier

        self._lock = threading.Lock()
        # When each recent failed send happened, oldest first. Empty while
        # backing off.
        self._failures = deque()
        # The length of the current pause, or zero when not backing off.
        self._delay = 0
        # When sending may start again.
        self._resume_at = None

    @property
    def backing_off(self):
        """!
        True from the start of a pause until a send succeeds.
        """
        with self._lock:
            return self._delay > 0

    def remaining(self, now):
        """!
        The seconds left before sending may start again, or zero if it may
        start now.
        """
        with self._lock:
            if self._resume_at is None or self._resume_at <= now:
                return 0
            return self._resume_at - now

    def failed(self, now):
        """!
        Record a failed send.

        @return: the new pause in seconds if this failure started or
        lengthened one, otherwise zero
        """
        with self._lock:
            if self._delay > 0:
                # The send tried when the last pause ended failed.
                self._delay = min(
                    self._delay * self.recovery_multiplier,
                    self.max_recovery_delay_seconds)
            else:
                self._failures.append(now)
                while self._failures[0] < now - self.failures_window_seconds:
                    self._failures.popleft()
                if len(self._failures) < self.failures_to_enter_recovery:
                    return 0
                self._failures.clear()
                self._delay = min(
                    self.initial_recovery_delay_seconds,
                    self.max_recovery_delay_seconds)
            self._resume_at = now + self._delay
            return self._delay

    def succeeded(self):
        """!
        Record a successful send.

        @return: True if this ended a back-off
        """
        with self._lock:
            if self._delay == 0:
                return False
            self._delay = 0
            self._resume_at = None
            return True
