from unittest.mock import patch

from odoo.exceptions import UserError

from .common import TestMessageSPV


class TestDownloadFromSPV(TestMessageSPV):
    def setUp(self):
        super(TestDownloadFromSPV, self).setUp()
        # Setup test records and environment
        self.MessageSPV = self.env["l10n.ro.message.spv"]
        self.Attachment = self.env["ir.attachment"]

        # Create a message_spv record for testing
        self.test_message_spv = self.MessageSPV.create(
            {
                "name": "Test Message",
                "company_id": self.env.company.id,
                "state": "draft",
            }
        )

    @patch("odoo.addons.l10n_ro_message_spv.models.message_spv.requests.post")
    def test_download_from_spv_success(self, mock_post):
        # Mock the response from the external service
        mock_response = mock_post.return_value
        mock_response.status_code = 200
        mock_response.content = b"Fake zip content"

        # Perform the method under test
        self.test_message_spv.download_from_spv()

        # Assertions to verify the outcome
        self.assertTrue(
            self.test_message_spv.attachment_id,
            "Attachment should be created on successful download.",
        )
        self.assertEqual(
            self.test_message_spv.state,
            "downloaded",
            "State should be 'downloaded' after successful download.",
        )

    @patch("odoo.addons.l10n_ro_message_spv.models.message_spv.requests.post")
    def test_download_from_spv_success_error(self, mock_post):
        # Mock the response from the external service
        mock_response = mock_post.return_value
        mock_response.status_code = 200
        mock_response.content = {"eroare": "Error message"}

        # Perform the method under test
        self.test_message_spv.download_from_spv()

        # Assertions to verify the outcome
        self.assertEqual(
            self.test_message_spv.error,
            "Error message.",
            "Error message should be saved on successful download.",
        )
        self.assertEqual(
            self.test_message_spv.state,
            "downloaded",
            "State should be 'downloaded' after successful download.",
        )

    @patch("odoo.addons.l10n_ro_message_spv.models.message_spv.requests.post")
    def test_download_from_spv_success_error_400(self, mock_post):
        # Mock the response from the external service
        mock_response = mock_post.return_value
        mock_response.status_code = 400
        mock_response.content = {"message": "Error message 400"}

        # Perform the method under test
        self.test_message_spv.download_from_spv()

        # Assertions to verify the outcome
        self.assertEqual(
            self.test_message_spv.error,
            "Error message 400.",
            "Error message should be saved on successful download.",
        )
        self.assertEqual(
            self.test_message_spv.state,
            "downloaded",
            "State should be 'downloaded' after successful download.",
        )

    def test_download_from_spv_no_config(self):
        # Simulate missing ANAF configuration
        self.env["l10n.ro.account.anaf.sync"].search([]).unlink()

        # Perform the method under test
        with self.assertRaises(
            UserError,
            msg="Should raise a UserError if the ANAF configuration is missing",
        ):
            self.test_message_spv.download_from_spv()
