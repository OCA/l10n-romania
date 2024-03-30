# Copyright (C) 2023 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from unittest.mock import Mock, patch

import requests

from odoo.tests.common import TransactionCase


class TestAccountANAFSync(TransactionCase):
    @classmethod
    def setUpClass(cls):
        cls._super_send = requests.Session.send
        super().setUpClass()

    @classmethod
    def _request_handler(cls, s, r, /, **kw):
        """Don't block external requests."""
        return cls._super_send(s, r, **kw)

    def setUp(self):
        super().setUp()
        self.test_company = self.env["res.company"].create({"name": "Test Sync"})
        self.sync = self.env["l10n.ro.account.anaf.sync"].create(
            {
                "company_id": self.test_company.id,
                "client_id": "123",
                "client_secret": "123",
            }
        )

    def _mocked_successful_empty_get_response(self, *args, **kwargs):
        """This mock is used when requesting documents, such as labels."""
        response = Mock()
        response.status_code = 200
        response.content = ""
        return response

    def test_anaf_api(self):
        with patch.object(requests, "get", self._mocked_successful_empty_get_response):
            self.sync.test_anaf_api()

    def test_revoke_access_token(self):
        self.sync.write({"access_token": "123"})
        with patch.object(requests, "post", self._mocked_successful_empty_get_response):
            self.sync.revoke_access_token()

    def test_get_access_token(self):
        with patch.object(requests, "post", self._mocked_successful_empty_get_response):
            self.sync.get_token_from_anaf_website()
