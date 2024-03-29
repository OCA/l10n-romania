# ©  2015-2021 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from unittest.mock import Mock, patch

import requests

from odoo import fields
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged("-at_install", "post_install")
class TestAnafSyncControllers(HttpCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.test_company = self.env["res.company"].create({"name": "Test Sync"})
        self.sync = self.env["l10n.ro.account.anaf.sync"].create(
            {
                "company_id": self.test_company.id,
                "client_id": "123",
                "client_secret": "123",
                "access_token": "123",
            }
        )

    def _mocked_successful_empty_get_response(self, *args, **kwargs):
        """This mock is used when requesting documents, such as labels."""
        response = Mock()
        response.status_code = 200
        response.content = ""
        return response

    def test_redirect_anaf(self):
        self.authenticate("demo", "demo")
        with mute_logger("odoo.http"):
            response = self.url_open(
                "/l10n_ro_account_anaf_sync/redirect_anaf/%s" % self.sync.id
            )
        self.assertTrue(response.status_code)

    def test_anaf_oauth(self):
        self.sync.write({"last_request_datetime": fields.Datetime.now()})
        with patch.object(requests, "post", self._mocked_successful_empty_get_response):
            with mute_logger("odoo.http"):
                response = self.url_open(
                    "/l10n_ro_account_anaf_sync/anaf_oauth/%s" % self.sync.id,
                    data={"code": "123"},
                )
            self.assertEqual(response.status_code, 200)
