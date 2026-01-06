# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from contextlib import contextmanager

from odoo import models
from odoo.fields import Command
from odoo.tools import float_compare


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def _get_sync_stack(self, container):
        def has_l10n_ro_non_deductible_lines(move):
            return move.state == "draft" and any(
                move.line_ids.filtered(
                    lambda line: line.display_type == "product"
                    and line.company_id.l10n_ro_accounting
                    and line.deductible_amount < 100
                )
            )

        ro_non_deductible_moves = container["records"].filtered(
            lambda m: has_l10n_ro_non_deductible_lines(m)
        )
        ro_non_deductible_container = {"records": ro_non_deductible_moves}
        stack, update_containers = super()._get_sync_stack(container)
        stack.append((64, self._sync_l10n_ro_tax_lines(ro_non_deductible_container)))
        stack.append(
            (
                65,
                self._l10n_ro_sync_non_deductible_base_lines(
                    ro_non_deductible_container
                ),
            )
        )
        return stack, update_containers

    def _get_l10n_ro_nd_repartition_lines(self, tax):
        self.ensure_one()
        rep_lines = tax.invoice_repartition_line_ids
        if self.is_purchase_document():
            rep_lines = (
                tax.invoice_repartition_line_ids
                if "refund" not in self.move_type
                else tax.refund_repartition_line_ids
            )
        elif self.stock_move_ids:
            if hasattr(self.stock_move_ids, "l10n_ro_move_type"):
                l10n_ro_move_type = self.stock_move_ids.l10n_ro_move_type
                types_allow_ndeductibility = [
                    "minus_inventory",
                    "consumption",
                    "consumption_return",
                    "usage_giving",
                    "usage_giving_return",
                ]
                if l10n_ro_move_type and "return" in l10n_ro_move_type:
                    rep_lines = tax.invoice_repartition_line_ids
                elif l10n_ro_move_type in types_allow_ndeductibility:
                    rep_lines = tax.refund_repartition_line_ids
        return rep_lines

    @contextmanager
    def _l10n_ro_sync_non_deductible_base_lines(self, container):
        yield
        to_delete = []
        to_create = []
        for move in container["records"]:
            if move.state != "draft":
                continue

            non_deductible_base_lines = move.line_ids.filtered(
                lambda line: line.display_type
                in ("non_deductible_product", "non_deductible_product_total")
            )
            if non_deductible_base_lines:
                to_delete += non_deductible_base_lines.ids

            sign = move.direction_sign
            rate = move.invoice_currency_rate

            for line in move.line_ids.filtered(
                lambda line: line.display_type == "product"
            ):
                if (
                    float_compare(line.deductible_amount, 100, precision_rounding=2)
                    == 0
                ):
                    continue

                percentage = 1 - line.deductible_amount / 100
                non_deductible_subtotal = line.currency_id.round(
                    line.balance * percentage
                )
                non_deductible_base = line.currency_id.round(
                    sign * non_deductible_subtotal
                )
                non_deductible_base_currency = (
                    line.company_currency_id.round(
                        sign * non_deductible_subtotal / rate
                    )
                    if rate
                    else sign * non_deductible_subtotal
                )
                tax = line.tax_ids.filtered(lambda t: t.amount_type != "fixed")
                rep_lines = move._get_l10n_ro_nd_repartition_lines(tax)
                base_rep_line = rep_lines.filtered(
                    lambda r: r.repartition_type == "base"
                )
                tax_tags = base_rep_line.mapped("tag_ids")
                to_create.append(
                    {
                        "move_id": move.id,
                        "account_id": line.account_id.id,
                        "display_type": "non_deductible_product",
                        "name": line.name,
                        "is_storno": True,
                        "balance": -1 * non_deductible_base,
                        "amount_currency": -1 * non_deductible_base_currency,
                        "l10n_ro_non_deductible_line_id": line.id,
                        "tax_ids": [Command.set([])],
                        "tax_tag_ids": [Command.set(tax_tags.ids)],
                        "tax_line_id": False,
                        "sequence": line.sequence + 1,
                    }
                )
                non_deductible_acc = line.account_id
                if non_deductible_acc.l10n_ro_nondeductible_account_id:
                    non_deductible_acc = (
                        non_deductible_acc.l10n_ro_nondeductible_account_id
                    )
                if not non_deductible_acc:
                    non_deductible_acc = (
                        move.journal_id.non_deductible_account_id
                        or move.journal_id.default_account_id
                    )
                to_create.append(
                    {
                        "move_id": move.id,
                        "account_id": non_deductible_acc.id,
                        "display_type": "non_deductible_product_total",
                        "name": self.env._("private part"),
                        "balance": non_deductible_base,
                        "amount_currency": non_deductible_base_currency,
                        "l10n_ro_non_deductible_line_id": line.id,
                        "tax_ids": [Command.set([])],
                        "tax_line_id": False,
                        "tax_tag_ids": [
                            Command.set(tax_tags.l10n_ro_nondeductible_tag_id.ids)
                        ],
                        "sequence": max(move.line_ids.mapped("sequence")) + 1,
                    }
                )
        while to_create and to_delete:
            line_data = to_create.pop()
            line_id = to_delete.pop()
            self.env["account.move.line"].browse(line_id).write(line_data)
        if to_create:
            self.env["account.move.line"].create(to_create)
        if to_delete:
            self.env["account.move.line"].browse(to_delete).with_context(
                dynamic_unlink=True
            ).unlink()

    @contextmanager
    def _sync_l10n_ro_tax_lines(self, container):
        yield

        to_delete = []
        to_create = []
        for move in container["records"]:
            if move.state != "draft":
                continue

            non_deductible_tax_lines = move.line_ids.filtered(
                lambda tax_line: tax_line.display_type
                in ["non_deductible_tax", "non_deductible_tax_ro"]
            )

            # Find non-deductible tax base lines
            if non_deductible_tax_lines:
                to_delete += non_deductible_tax_lines.ids

            for line in move.line_ids.filtered(
                lambda line: line.display_type == "product"
            ):
                if (
                    float_compare(line.deductible_amount, 100, precision_rounding=2)
                    == 0
                ):
                    continue
                taxes = line.tax_ids.filtered(lambda t: t.amount_type != "fixed")
                # Calculate 100% tax for this line
                for tax in taxes:
                    line_tax_values = tax.compute_all(
                        line.price_unit,
                        currency=line.currency_id,
                        quantity=line.quantity,
                        product=line.product_id,
                        partner=move.partner_id,
                    )
                    line_tax_amount = (
                        line_tax_values["total_included"]
                        - line_tax_values["total_excluded"]
                    )
                    if line_tax_amount == 0 and line.balance != 0:
                        line_tax_values = tax.compute_all(
                            line.balance,
                            currency=line.currency_id,
                            quantity=1,
                            product=line.product_id,
                            partner=move.partner_id,
                        )
                        line_tax_amount = (
                            line_tax_values["total_included"]
                            - line_tax_values["total_excluded"]
                        )
                    tax_amount = line.currency_id.round(line_tax_amount)
                    # For each tax distributed on this line, create:
                    rep_lines = move._get_l10n_ro_nd_repartition_lines(tax)
                    for tax_repartition_line in rep_lines:
                        if tax_repartition_line.repartition_type != "tax":
                            continue
                        tax_line_amount = (
                            tax_amount
                            * tax_repartition_line.factor
                            * (100 - line.deductible_amount)
                            / 100
                        )
                        to_create.append(
                            {
                                "move_id": move.id,
                                "account_id": tax_repartition_line.account_id.id,
                                "display_type": "non_deductible_tax_ro",
                                "name": tax.name,
                                "is_storno": True,
                                "balance": -1 * tax_line_amount * move.direction_sign,
                                "amount_currency": -1
                                * tax_line_amount
                                * move.direction_sign,
                                "sequence": max(move.line_ids.mapped("sequence")) + 1,
                                "l10n_ro_non_deductible_line_id": line.id,
                                "tax_tag_ids": [
                                    Command.set(tax_repartition_line.tag_ids.ids)
                                ],
                            }
                        )
                        account = (
                            move.company_id.l10n_ro_nondeductible_account_id
                            or move.journal_id.non_deductible_account_id
                            or tax_repartition_line.account_id
                        )
                        to_create.append(
                            {
                                "move_id": move.id,
                                "account_id": account.id,
                                "display_type": "non_deductible_tax_ro",
                                "name": f"{tax.name} (non-deductible total)",
                                "balance": tax_line_amount * move.direction_sign,
                                "amount_currency": tax_line_amount
                                * move.direction_sign,
                                "sequence": max(move.line_ids.mapped("sequence")) + 2,
                                "l10n_ro_non_deductible_line_id": line.id,
                                "tax_tag_ids": [
                                    Command.set(
                                        tax_repartition_line.tag_ids.mapped(
                                            "l10n_ro_nondeductible_tag_id"
                                        ).ids
                                    )
                                ],
                            }
                        )

        if to_delete:
            self.env["account.move.line"].browse(to_delete).with_context(
                dynamic_unlink=True
            ).unlink()
        if to_create:
            self.env["account.move.line"].create(to_create)

    def _inverse_tax_totals(self):
        ro_moves = self.filtered(lambda m: m.company_id.l10n_ro_accounting)
        res = True
        if self - ro_moves:
            res = super(AccountMove, self - ro_moves)._inverse_tax_totals()
        with ro_moves._disable_recursion(
            {"records": ro_moves}, "skip_invoice_sync"
        ) as disabled:
            if disabled:
                return
        with ro_moves._sync_dynamic_line(
            existing_key_fname="term_key",
            needed_vals_fname="needed_terms",
            needed_dirty_fname="needed_terms_dirty",
            line_type="payment_term",
            container={"records": ro_moves},
        ):
            moves_with_subtotal = ro_moves.filtered(
                lambda m: m.tax_totals and "subtotals" in m.tax_totals
            )
            super(AccountMove, moves_with_subtotal)._inverse_tax_totals()
        return res
