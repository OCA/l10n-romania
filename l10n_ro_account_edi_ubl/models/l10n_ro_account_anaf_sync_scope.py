import logging

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountANAFSyncScope(models.Model):
    _inherit = "l10n.ro.account.anaf.sync.scope"

    scope = fields.Selection(selection_add=[("e-factura", "E-factura")])

    @api.onchange("scope")
    def _onchange_scope(self):
        res = super()._onchange_scope()
        if self.scope == "e-factura":
            self.anaf_sync_test_url = "https://api.anaf.ro/test/FCTEL/rest"
            self.anaf_sync_production_url = "https://api.anaf.ro/prod/FCTEL/rest"
        return res

    def _l10n_ro_einvoice_call(self, func, params, data=None, method="POST"):
        self.ensure_one()
        _logger.info("ANAF API call: %s %s" % (func, params))
        url = self.anaf_sync_url + func
        access_token = self.anaf_sync_id.access_token
        headers = {
            "Content-Type": "application/xml",
            "Authorization": f"Bearer {access_token}",
        }
        test_data = self.env.context.get("test_data", False)
        if test_data:
            content = test_data
            status_code = 200
        else:
            if method == "GET":
                response = requests.get(
                    url, params=params, data=data, headers=headers, timeout=80
                )
            else:
                response = requests.post(
                    url, params=params, data=data, headers=headers, timeout=80
                )

            content = response.content
            status_code = response.status_code
            if response.status_code == 400:
                content = response.json()
            content_type = ""
            if response.headers:
                content_type = response.headers.get("Content-Type", "")
            if content_type == "application/xml":
                _logger.info("ANAF API response: %s" % response.text)
            if "text/plain" in content_type:
                try:
                    content = response.json()
                    if content.get("eroare"):
                        status_code = 400
                except Exception:
                    _logger.info("ANAF API response: %s" % response.text)

        return content, status_code
