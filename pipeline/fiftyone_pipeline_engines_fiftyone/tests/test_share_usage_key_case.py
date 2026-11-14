import unittest

from fiftyone_pipeline_core.pipelinebuilder import PipelineBuilder
from fiftyone_pipeline_engines_fiftyone.share_usage import ShareUsage


class ShareUsageKeyCaseTests(unittest.TestCase):

    def test_session_id_and_sequence_are_recorded_whatever_their_case(self):
        """
        Evidence keys ignore letter case, so the session id and sequence are
        the record's SessionId and Sequence whatever the letters of their keys.
        """
        element = ShareUsage(requested_package_size=1000)
        self.addCleanup(element.close)
        pipeline = PipelineBuilder().add(element).build()
        for session_key, sequence_key in (
                ("query.session-id", "query.sequence"),
                ("query.Session-Id", "query.Sequence")):
            flow_data = pipeline.create_flowdata()
            flow_data.evidence.add("header.user-agent", "agent")
            flow_data.evidence.add(session_key, "the session")
            flow_data.evidence.add(sequence_key, "2")
            data = element.get_data_from_evidence(flow_data)
            self.assertEqual("the session", data.session_id, session_key)
            self.assertEqual(2, data.sequence, sequence_key)


if __name__ == "__main__":
    unittest.main()
