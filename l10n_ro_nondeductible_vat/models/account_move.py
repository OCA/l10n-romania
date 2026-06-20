# Copyright (C) 2021 Dakai Soft SRL
# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from collections import defaultdict
from contextlib import contextmanager

from odoo import models
from odoo.fields import Command
from odoo.tools import float_compare


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.ro.mixin"]

    def _post(self, soft=True):
        # Realize the deferred non-deductibility on the cash-basis entry that
        # is generated at payment for VAT-on-payment taxes. On the invoice the
        # split is skipped (see _get_sync_stack); it materializes here, when the
        # VAT becomes deductible.
        self._l10n_ro_split_cash_basis_non_deductible()
        return super()._post(soft=soft)

    def _l10n_ro_nd_fraction_from_origin(self, origin):
        """Map {tax_id: non_deductible_fraction} for the on-payment taxes of
        the originating invoice. The fraction is weighted by base, so several
        product lines sharing the same tax with different deductibilities are
        handled correctly (the cash-basis VAT is aggregated per tax)."""
        nd_base = defaultdict(float)
        total_base = defaultdict(float)
        for line in origin.line_ids.filtered(
            lambda line: line.display_type == "product"
        ):
            for tax in line.tax_ids.filtered(
                lambda t: t.amount_type != "fixed"
                and t.tax_exigibility == "on_payment"
                and t.l10n_ro_is_nondeductible
            ):
                base = abs(line.balance)
                total_base[tax.id] += base
                nd_base[tax.id] += base * (1 - line.deductible_amount / 100.0)
        return {
            tax_id: nd_base[tax_id] / total_base[tax_id]
            for tax_id in total_base
            if total_base[tax_id] and nd_base[tax_id]
        }

    @staticmethod
    def _l10n_ro_debit_credit(balance):
        return (balance, 0.0) if balance > 0.0 else (0.0, -balance)

    def _l10n_ro_split_cash_basis_non_deductible(self):
        for move in self:
            origin = move.tax_cash_basis_origin_move_id
            if (
                not origin
                or move.state != "draft"
                or not move.company_id.l10n_ro_accounting
            ):
                continue
            nd_fraction = move._l10n_ro_nd_fraction_from_origin(origin)
            if not nd_fraction:
                continue
            nd_account = move.company_id.l10n_ro_nondeductible_account_id
            new_lines = []
            to_delete = self.env["account.move.line"]
            # Core matches the cash-basis counterpart lines by their sequence
            # number, so keep the extra lines well outside that range.
            next_sequence = max(move.line_ids.mapped("sequence") or [0]) + 100
            for line in move.line_ids:
                tax = line.tax_line_id
                is_tax_line = (
                    tax
                    and tax.id in nd_fraction
                    and line.tax_repartition_line_id.repartition_type == "tax"
                )
                base_taxes = line.tax_ids.filtered(lambda t, nd=nd_fraction: t.id in nd)
                is_base_grid_line = not tax and line.tax_tag_ids and base_taxes
                if not is_tax_line and not is_base_grid_line:
                    continue

                frac = nd_fraction[tax.id if is_tax_line else base_taxes[:1].id]
                nd_balance = move.company_currency_id.round(line.balance * frac)
                nd_amount_cur = line.currency_id.round(line.amount_currency * frac)
                if not nd_balance and not nd_amount_cur:
                    continue

                if is_tax_line:
                    # Move the non-deductible part of the VAT to expense.
                    target_acc = nd_account or line.account_id
                    nd_tags = line.tax_repartition_line_id.tag_ids.mapped(
                        "l10n_ro_nondeductible_tag_id"
                    )
                    display_type = "non_deductible_tax_ro"
                    name = self.env._("%(tax)s (non-deductible)", tax=tax.name)
                else:
                    # Reclass the corresponding base from the deductible grid
                    # (e.g. 24 - TAX BASE) to the non-deductible one (24_2).
                    target_acc = line.account_id
                    nd_tags = line.tax_tag_ids.mapped("l10n_ro_nondeductible_tag_id")
                    display_type = line.display_type
                    name = line.name
                if not nd_tags:
                    continue

                remaining_balance = line.balance - nd_balance
                remaining_currency = line.amount_currency - nd_amount_cur
                if move.company_currency_id.is_zero(
                    remaining_balance
                ) and line.currency_id.is_zero(remaining_currency):
                    # Fully non-deductible: the deductible line vanishes.
                    to_delete |= line
                else:
                    debit, credit = self._l10n_ro_debit_credit(remaining_balance)
                    line.write(
                        {
                            "debit": debit,
                            "credit": credit,
                            "amount_currency": remaining_currency,
                        }
                    )
                nd_debit, nd_credit = self._l10n_ro_debit_credit(nd_balance)
                new_lines.append(
                    Command.create(
                        {
                            "account_id": target_acc.id,
                            "name": name,
                            "display_type": display_type,
                            "debit": nd_debit,
                            "credit": nd_credit,
                            "amount_currency": nd_amount_cur,
                            "currency_id": line.currency_id.id,
                            "partner_id": line.partner_id.id,
                            "tax_tag_ids": [Command.set(nd_tags.ids)],
                            "sequence": next_sequence,
                        }
                    )
                )
                next_sequence += 1
            if new_lines:
                move.write({"line_ids": new_lines})
            if to_delete:
                to_delete.with_context(dynamic_unlink=True).unlink()

    def _l10n_ro_line_is_on_payment(self, line):
        # VAT on payment (cash basis): non-deductibility is only realized when
        # the invoice is paid, so it must NOT be split on the invoice itself.
        # It is handled later on the cash-basis entry (see
        # account.partial.reconcile).
        return any(
            tax.tax_exigibility == "on_payment"
            for tax in line.tax_ids.filtered(lambda t: t.amount_type != "fixed")
        )

    def _get_sync_stack(self, container):
        def has_l10n_ro_non_deductible_lines(move):
            # Note: on-payment lines are intentionally kept here so the RO sync
            # runs and removes the core non-deductible lines for them; the
            # actual reversal is then skipped (deferred to the cash-basis
            # entry) inside the sync creation loops.
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
        # Runs last (lowest priority => unwound last): the core non-deductible
        # syncs (priorities 50/60) recreate the non-deductible lines after the
        # RO syncs above, so for on-payment (cash basis) taxes we strip them
        # here as the final step. Their non-deductibility is realized on the
        # cash-basis entry generated at payment instead.
        stack.append(
            (45, self._l10n_ro_drop_on_payment_non_deductible_lines(container))
        )
        return stack, update_containers

    @contextmanager
    def _l10n_ro_drop_on_payment_non_deductible_lines(self, container):
        yield
        to_delete = self.env["account.move.line"]
        for move in container["records"]:
            if move.state != "draft" or not move.company_id.l10n_ro_accounting:
                continue
            has_on_payment = move.line_ids.filtered(
                lambda line, move=move: line.display_type == "product"
                and line.deductible_amount < 100
                and move._l10n_ro_line_is_on_payment(line)
            )
            if not has_on_payment:
                continue
            # A document cannot mix on-payment and on-invoice taxes, so every
            # non-deductible line present here belongs to the deferred (cash
            # basis) flow and must be stripped from the invoice. It is the core
            # syncs (priorities 50/60) that recreate these after the RO syncs,
            # hence this final cleanup step (lowest priority).
            to_delete |= move.line_ids.filtered(
                lambda line: line.display_type
                in (
                    "non_deductible_product",
                    "non_deductible_product_total",
                    "non_deductible_tax",
                )
            )
        if to_delete:
            to_delete.with_context(dynamic_unlink=True).unlink()

    def _prepare_non_deductible_base_lines_for_taxes_computation_from_base_lines(
        self, base_lines
    ):
        # Skip on-payment (cash basis) lines: their non-deductibility is
        # deferred to the payment entry, so no non-deductible base/tax line
        # should be anticipated on the invoice.
        if self.company_id.l10n_ro_accounting:
            base_lines = base_lines.filtered(
                lambda line: not self._l10n_ro_line_is_on_payment(line)
            )
        return super()._prepare_non_deductible_base_lines_for_taxes_computation_from_base_lines(  # noqa: E501
            base_lines
        )

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
                if move._l10n_ro_line_is_on_payment(line):
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
                if move._l10n_ro_line_is_on_payment(line):
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
