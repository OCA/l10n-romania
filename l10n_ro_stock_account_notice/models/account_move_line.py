# Copyright (C) 2022 cbssolutions.ro
# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_ro_notice_invoice_difference = fields.Boolean(
        help="Used to know that are notice-invoice price differences. Used at validation and setting to draft"
    )

    def _get_computed_account(self):
        # triggered at onchange of product_id invoice/bill line creation
        # gives the account 408 or 418 if the product is in notice_pickings_ids
        if (
            self.product_id.type == "product"
            and self.is_l10n_ro_record
            and self.product_id.valuation == "real_time"
        ):
            if self.move_id.move_type in [
                "in_invoice",
                "in_refund",
            ] and self.move_id.l10n_ro_bill_for_pickings_ids.move_lines.filtered(
                lambda r: r.product_id == self.product_id
            ):
                # product in notice_pickings
                acc_bill_to_recieve = self.company_id.l10n_ro_property_bill_to_receive
                if not acc_bill_to_recieve:
                    raise ValidationError(
                        _(
                            "Go to Settings/config/romania and set the property bill to receive to 408."
                        )
                    )
                return acc_bill_to_recieve
            if self.move_id.move_type in [
                "out_invoice",
                "out_refund",
            ] and self.move_id.l10n_ro_invoice_for_pickings_ids.move_lines.filtered(
                lambda r: r.product_id == self.product_id
            ):
                # product in notice_pickings
                acc_invoice_to_create = (
                    self.company_id.l10n_ro_property_invoice_to_create
                )
                if not acc_invoice_to_create:
                    raise ValidationError(
                        _(
                            "Go to Settings/config/romania and set the property invoice to create to 418."
                        )
                    )
                return acc_invoice_to_create

        return super(AccountMoveLine, self)._get_computed_account()
