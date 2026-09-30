# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ("account.move", "l10n.ro.mixin")

    l10n_ro_extra_stock_move_id = fields.Many2one(
        "stock.move",
        string="Romania - Extra Stock Move",
        readonly=True,
    )
    fifo_neg_origin_move_id = fields.Many2one(
        "stock.move",
        string="Source IN move for negative stock compensation",
        index="btree_not_null",
        readonly=True,
        copy=False,
        help="The incoming stock move that triggered this FIFO negative "
        "stock compensation accounting entry.",
    )

    def _get_cogs_lines_vals(self):
        """Romania does not discharge inventory when the invoice is posted.

        The stock move books 607 against 371 when the goods leave, so the COGS
        pair Odoo adds on the customer invoice would relieve the same goods a
        second time. Odoo 19 suppressed it in
        ``_stock_account_prepare_realtime_out_lines_vals``; Odoo 20 builds the
        lines here instead.
        """
        self.ensure_one()
        if self.is_l10n_ro_record:
            return []
        return super()._get_cogs_lines_vals()

    def _get_price_difference_lines_vals(self):
        """The Romanian price difference has its own module.

        ``l10n_ro_stock_price_difference`` decides what a bill priced
        differently from the reception does to inventory, so the Anglo-Saxon
        pair Odoo would add on the bill has no place here. Odoo 19 suppressed
        it in ``_stock_account_prepare_anglo_saxon_in_lines_vals``.
        """
        self.ensure_one()
        if self.company_id.l10n_ro_accounting:
            return []
        return super()._get_price_difference_lines_vals()

    def _l10n_ro_prepare_notice_rate_difference_vals(self):
        """Values for the lines recognising the exchange rate difference on
        the 408 pivot.

        Per OMFP 1802/2014, account 408 is debited with "the value of the
        invoices received (401)" and with the favourable exchange rate
        differences "recorded when the invoice is received" (765), and
        credited with the unfavourable ones (665). The bill line debits 408 at
        the invoice rate, so the difference up to the amount credited at
        reception is booked here and the pivot closes for the rate part - no
        reconciliation needed, which is why 408 does not have to be a
        reconcilable account.

        The lines are `cogs` lines on the bill itself, like the native price
        difference in `stock_account`: each pair balances, so the invoice
        total is untouched, they stay out of the e-invoice and they are
        removed when the bill is reset to draft.
        """
        vals_list = []
        for move in self:
            if move.move_type not in ("in_invoice", "in_refund"):
                continue
            for line in move.invoice_line_ids:
                rate_diff = line._l10n_ro_notice_rate_difference()
                if not move.company_id.currency_id.is_zero(rate_diff):
                    vals_list += line._l10n_ro_rate_difference_line_vals(rate_diff)
        return vals_list

    def _post(self, soft=True):
        if not self.env.context.get("move_reverse_cancel"):
            ro_bills = self.filtered(lambda m: m.is_l10n_ro_record)
            rate_diff_vals = ro_bills._l10n_ro_prepare_notice_rate_difference_vals()
            if rate_diff_vals:
                self.env["account.move.line"].create(rate_diff_vals)
        return super()._post(soft=soft)

    def _compute_is_storno(self):
        # EXTENDS 'account' for Romania
        # Stock moves with 'return' type or plus_inventory are considered storno
        res = super()._compute_is_storno()
        for move in self:
            if move.is_l10n_ro_record:
                stock_moves = move.line_ids._get_stock_moves()
                if stock_moves and all(
                    "return" in (m.l10n_ro_move_type or "")
                    or m.l10n_ro_move_type == "plus_inventory"
                    for m in stock_moves
                ):
                    move.is_storno = True
        return res
