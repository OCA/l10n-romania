# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "l10n.ro.mixin"]

    @api.model
    def _get_valued_types(self):
        valued_types = super(StockMove, self)._get_valued_types()
        if not self.filtered("is_l10n_ro_record"):
            return valued_types

        valued_types += [
            "reception_notice",  # receptie de la furnizor cu aviz
            "reception_notice_return",  # retur receptie de la furnizor cu aviz
            "delivery_notice",
            "delivery_notice_return",
        ]
        return valued_types

    def _is_reception(self):
        """Este receptie in stoc fara aviz"""
        if not self.is_l10n_ro_record:
            return super(StockMove, self)._is_reception()

        it_is = (
            super(StockMove, self)._is_reception()
            and not self.picking_id.l10n_ro_notice
        )
        return it_is

    def _is_reception_return(self):
        """Este un retur la o receptie in stoc fara aviz"""
        if not self.is_l10n_ro_record:
            return super(StockMove, self)._is_reception_return()

        it_is = (
            super(StockMove, self)._is_reception_return()
            and not self.picking_id.l10n_ro_notice
        )
        return it_is

    def _is_reception_notice(self):
        """Este receptie in stoc cu aviz"""
        if not self.is_l10n_ro_record:
            return super(StockMove, self)._is_reception_return()

        it_is = (
            self.company_id.l10n_ro_accounting
            and self.picking_id.l10n_ro_notice
            and self.location_id.usage == "supplier"
            and self._is_in()
        )
        return it_is

    def _create_reception_notice_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="reception_notice")
        return move._create_in_svl(forced_quantity)

    def _is_reception_notice_return(self):
        """Este un retur la receptie in stoc cu aviz"""
        if not self.is_l10n_ro_record:
            return False

        it_is = (
            self.company_id.l10n_ro_accounting
            and self.picking_id.l10n_ro_notice
            and self.location_dest_id.usage == "supplier"
            and self._is_out()
        )
        return it_is

    def _create_reception_notice_return_svl(self, forced_quantity=None):
        svl = self.env["stock.valuation.layer"]
        for move in self:
            move = move.with_context(
                standard=True, valued_type="reception_notice_return"
            )
            if (
                move.origin_returned_move_id
                and move.origin_returned_move_id.sudo().stock_valuation_layer_ids
            ):
                move = move.with_context(
                    origin_return_candidates=move.origin_returned_move_id.sudo()
                    .stock_valuation_layer_ids.filtered(lambda sv: sv.remaining_qty > 0)
                    .ids
                )
            svl += move._create_out_svl(forced_quantity)
        return svl

    def _is_delivery(self):
        """Este livrare din stoc fara aviz"""
        if not self.is_l10n_ro_record:
            return super(StockMove, self)._is_delivery()

        return (
            super(StockMove, self)._is_delivery() and not self.picking_id.l10n_ro_notice
        )

    def _is_delivery_return(self):
        """Este retur la o livrare din stoc fara aviz"""
        if not self.is_l10n_ro_record:
            return super(StockMove, self)._is_delivery_return()

        it_is = (
            super(StockMove, self)._is_delivery_return()
            and not self.picking_id.l10n_ro_notice
        )
        return it_is

    def _is_delivery_notice(self):
        """Este livrare cu aviz"""
        if not self.is_l10n_ro_record:
            return False

        it_is = (
            self.company_id.l10n_ro_accounting
            and self.picking_id.l10n_ro_notice
            and self.location_dest_id.usage == "customer"
            and self._is_out()
        )
        return it_is

    def _create_delivery_notice_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery_notice")
        return move._create_out_svl(forced_quantity)

    def _is_delivery_notice_return(self):
        """Este retur livrare cu aviz"""
        if not self.is_l10n_ro_record:
            return False

        it_is = (
            self.company_id.l10n_ro_accounting
            and self.picking_id.l10n_ro_notice
            and self.location_id.usage == "customer"
            and self._is_in()
        )
        return it_is

    def _create_delivery_notice_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery_notice_return")
        return move._create_in_svl(forced_quantity)

    def _romanian_account_entry_move(self, qty, description, svl_id, cost):
        res = super()._romanian_account_entry_move(qty, description, svl_id, cost)
        svl = self.env["stock.valuation.layer"]
        if self._is_delivery_notice():
            # inregistrare valoare vanzare
            sale_price = -1 * self._l10n_ro_get_sale_price()
            move = self.with_context(valued_type="invoice_out_notice")

            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = move._get_accounting_data_for_valuation()
            move._create_account_move_line(
                acc_valuation,
                acc_dest,
                journal_id,
                qty,
                description,
                svl,
                qty * sale_price,
            )

        if self._is_delivery_notice_return():
            # inregistrare valoare vanzare
            sale_price = self._l10n_ro_get_sale_price()
            move = self.with_context(valued_type="invoice_out_notice")

            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = move._get_accounting_data_for_valuation()
            move._create_account_move_line(
                acc_dest,
                acc_valuation,
                journal_id,
                qty,
                description,
                svl_id,
                qty * sale_price,
            )
        return res

    def _l10n_ro_get_sale_price(self):
        mv_date = self.date

        Module = self.env["ir.module.module"]
        is_installed = Module.search(
            [("name", "=", "l10n_ro_stock_account_date"), ("state", "=", "installed")]
        )
        if is_installed:
            mv_date = self.l10n_ro_get_move_date()

        valuation_amount = 0
        sale_line = self.sale_line_id
        if sale_line and sale_line.product_uom_qty:
            price_invoice = sale_line.price_subtotal / sale_line.product_uom_qty
            price_invoice = sale_line.product_uom._compute_price(
                price_invoice, self.product_uom
            )
            valuation_amount = price_invoice
            company = self.location_id.company_id or self.env.company
            valuation_amount = sale_line.order_id.currency_id._convert(
                valuation_amount, company.currency_id, company, mv_date
            )
        return valuation_amount

    def _get_accounting_data_for_valuation(self):
        journal_id, acc_src, acc_dest, acc_valuation = super(
            StockMove, self
        )._get_accounting_data_for_valuation()
        if (
            self.is_l10n_ro_record
            and self.product_id.categ_id.l10n_ro_stock_account_change
        ):
            location_from = self.location_id
            location_to = self.location_dest_id
            valued_type = self.env.context.get("valued_type", "indefinite")

            # in nir si factura se ca utiliza 408
            if valued_type == "invoice_in_notice":
                if location_to.l10n_ro_property_account_expense_location_id:
                    acc_dest = (
                        acc_valuation
                    ) = location_to.l10n_ro_property_account_expense_location_id.id
                # if location_to.property_account_expense_location_id:
                #     acc_dest = (
                #         acc_valuation
                #     ) = location_to.property_account_expense_location_id.id
            elif valued_type == "invoice_out_notice":
                if location_to.l10n_ro_property_account_income_location_id:
                    acc_valuation = acc_dest
                    acc_dest = (
                        location_to.l10n_ro_property_account_income_location_id.id
                    )
                if location_from.l10n_ro_property_account_income_location_id:
                    acc_valuation = (
                        location_from.l10n_ro_property_account_income_location_id.id
                    )

            # in Romania iesirea din stoc de face de regula pe contul de cheltuiala
            elif valued_type in [
                "delivery_notice",
            ]:
                acc_dest = (
                    location_from.l10n_ro_property_account_expense_location_id.id
                    or acc_dest
                )
            elif valued_type in [
                "delivery_notice_return",
            ]:
                acc_src = (
                    location_to.l10n_ro_property_account_expense_location_id.id
                    or acc_src
                )
        return journal_id, acc_src, acc_dest, acc_valuation
