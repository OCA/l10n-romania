# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from itertools import groupby

from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "l10n.ro.mixin"]

    l10n_ro_reception_in_progress = fields.Boolean(
        string="Romania - Reception in progress"
    )

    def action_create_reception_in_progress_invoice(self):
        """Create the reception in progress invoice associated to the PO."""
        self.env["decimal.precision"].precision_get("Product Unit of Measure")
        self = self.with_context(
            l10n_ro_reception_in_progress=True, valued_type="reception_in_progress"
        )
        # 1) Prepare invoice vals and clean-up the section lines
        invoice_vals_list = []
        sequence = 10
        for order in self:
            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_invoice()
            # Invoice line values (keep only necessary sections).
            for line in order.order_line:
                if line.display_type == "line_section":
                    pending_section = line
                    continue
                if pending_section:
                    line_vals = pending_section._prepare_account_move_line()
                    line_vals.update({"sequence": sequence})
                    invoice_vals["invoice_line_ids"].append((0, 0, line_vals))
                    sequence += 1
                    pending_section = None
                line_vals = line._prepare_account_move_line()
                line_vals.update({"quantity": line.product_qty})
                line_vals.update({"sequence": sequence})
                invoice_vals["invoice_line_ids"].append((0, 0, line_vals))
                sequence += 1
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(
                _(
                    "There is no invoiceable line. If a product has a control"
                    " policy based on received quantity, please make sure that"
                    " a quantity has been received."
                )
            )

        # 2) group by (company_id, partner_id, currency_id) for batch creation
        new_invoice_vals_list = []
        for _grouping_keys, invoices in groupby(
            invoice_vals_list,
            key=lambda x: (
                x.get("company_id"),
                x.get("partner_id"),
                x.get("currency_id"),
            ),
        ):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals["invoice_line_ids"] += invoice_vals[
                        "invoice_line_ids"
                    ]
                origins.add(invoice_vals["invoice_origin"])
                payment_refs.add(invoice_vals["payment_reference"])
                refs.add(invoice_vals["ref"])
            ref_invoice_vals.update(
                {
                    "ref": ", ".join(refs)[:2000],
                    "invoice_origin": ", ".join(origins),
                    "payment_reference": len(payment_refs) == 1
                    and payment_refs.pop()
                    or False,
                }
            )
            new_invoice_vals_list.append(ref_invoice_vals)
        invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.
        moves = self.env["account.move"]
        AccountMove = self.env["account.move"].with_context(
            default_move_type="in_invoice"
        )
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals["company_id"]).create(vals)

        # 4) Some moves might actually be refunds: convert them if the total
        # amount is negative. We do this after the moves have been created
        # since we need taxes, etc. to know if the total is actually negative or not
        moves.filtered(
            lambda m: m.currency_id.round(m.amount_total) < 0
        ).action_switch_move_type()
        self.l10n_ro_reception_in_progress = True
        return self.action_view_invoice(moves)

    def action_create_invoice(self):
        if len(self) == 1 and self.l10n_ro_reception_in_progress:
            self = self.with_context(
                l10n_ro_reception_in_progress=True, valued_type="reception_in_progress"
            )
        return super().action_create_invoice()
