# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        ro_price_diff_records = self.filtered(
            lambda m: m._should_generate_ro_price_difference()
        )
        if not ro_price_diff_records:
            return super().action_post()
        # Get price differences to process for each invoice
        price_diffs = ro_price_diff_records._get_l10n_ro_price_differences()
        if len(ro_price_diff_records) == 1 and not self.env.context.get(
            "l10n_ro_approved_price_difference"
        ):
            action = ro_price_diff_records._l10n_ro_get_price_difference_check_action(
                price_diffs
            )
            if action:
                return action

        res = super().action_post()
        ro_price_diff_records.l10n_ro_fix_price_difference_value(price_diffs)
        return res

    def _should_generate_ro_price_difference(self):
        self.ensure_one()
        if (
            self.move_type in ["in_invoice", "in_refund"]
            and self.company_id.l10n_ro_accounting
            and self.company_id.l10n_ro_stock_acc_price_diff
        ):
            return True
        return False

    def _get_l10n_ro_price_differences(self):
        """Return a dictionary mapping invoice IDs to a list of price difference
        items. Each item is a dictionary with the following keys
        - invoice_id
        - invoice_line_id
        - product_id
        - value_diff
        - qty_diff
        - stock_move
        """
        price_diffs = {}
        for invoice in self:
            invoice_price_diffs = []
            invoice_lines = invoice.invoice_line_ids.filtered(
                lambda line: line.display_type == "product" and line.purchase_line_id
            )
            for line in invoice_lines:
                diff_dict = line.l10n_ro_get_stock_valuation_difference()
                price_diff = diff_dict["value_diff"]
                if float_is_zero(
                    price_diff, precision_rounding=invoice.currency_id.rounding
                ):
                    continue
                line_diff_dict = diff_dict
                line_diff_dict.update(
                    {
                        "invoice_id": invoice.id,
                        "invoice_line_id": line.id,
                        "product_id": line.product_id.id,
                    }
                )
                invoice_price_diffs.append(line_diff_dict)
            if invoice_price_diffs:
                price_diffs[invoice.id] = invoice_price_diffs
        return price_diffs

    def _l10n_ro_get_price_difference_check_action(self, price_diffs=None):
        self.ensure_one()
        if not price_diffs:
            return False
        inv_price_diffs = price_diffs.get(self.id, [])

        if inv_price_diffs:
            difference_confirm_dialog_value = {
                "invoice_id": self.id,
                "item_ids": [],
            }
            for pd in inv_price_diffs:
                difference_confirm_dialog_value["item_ids"].append([0, 0, pd])

            wizard = self.env["l10n_ro.price_difference_confirm_dialog"].create(
                difference_confirm_dialog_value
            )

            action = self.env["ir.actions.actions"]._for_xml_id(
                "l10n_ro_stock_price_difference.action_price_difference_confirmation"
            )
            action["res_id"] = wizard.id

            return action
        return False

    def l10n_ro_fix_price_difference_value(self, price_diffs=None):
        if not price_diffs:
            return
        supp_invoices = self.filtered(
            lambda inv: inv.is_l10n_ro_record
            and inv.state == "posted"
            and inv.move_type in ["in_invoice", "in_refund"]
            and inv.company_id.l10n_ro_stock_acc_price_diff
        )
        for invoice in supp_invoices:
            inv_price_diffs = price_diffs.get(invoice.id, [])
            if not inv_price_diffs:
                continue
            for line in invoice.invoice_line_ids:
                line_price_diffs = {}
                for price_diff in inv_price_diffs:
                    if price_diff["invoice_line_id"] == line.id:
                        line_price_diffs = price_diff
                        break
                if not line_price_diffs:
                    continue
                line.l10n_ro_modify_stock_value(line_price_diffs)
