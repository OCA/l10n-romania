# Copyright (C) 2016 Forest and Biomass Romania
# Copyright (C) 2022 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

from .mt940 import MT940Parser as Parser

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def _parse_file(self, data_file):
        """Parse a MT940 IBAN BCR file."""
        parser = Parser()

        try:
            _logger.debug("Try parsing with MT940 IBAN BCR.")
            data = parser.parse(data_file)
            return self._post_parse_file(data)
        except ValueError:
            # Returning super will call next candidate:
            _logger.debug("Statement file was not a MT940 IBAN BCR file.", exc_info=True)
            return super(AccountBankStatementImport, self)._parse_file(data_file)

    def _post_parse_file(self, data):
        currency, account_num, all_statements = data
        for statements in all_statements:
            for transaction in statements["transactions"]:
                vat = transaction.pop("vat", False)
                if vat:
                    domain = [("vat", "like", vat), ("is_company", "=", True)]
                    partner = self.env["res.partner"].search(domain, limit=1)
                    if partner:
                        transaction["partner_name"] = partner.name
                        transaction["partner_id"] = partner.id
        return data
