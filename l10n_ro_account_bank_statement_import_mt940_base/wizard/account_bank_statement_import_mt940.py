# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _parse_file(self, data_file):
        parser = self.env["l10n.ro.account.bank.statement.import.mt940.parser"]
        if "type" not in self.env.context:
            parser = parser.with_context(type="mt940_general")
        # This runs for every company's import. A file in another format must
        # not crash the whole import: on any parse error fall back to the next
        # handler instead of propagating.
        try:
            data = parser.parse(data_file)
        except Exception as exc:  # noqa: BLE001
            _logger.debug("MT940 parser skipped this file: %s", exc)
            data = None
        if data:
            return data
        return super()._parse_file(data_file)
