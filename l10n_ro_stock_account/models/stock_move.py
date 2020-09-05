# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model
    def _get_valued_types(self):
        valued_types = super(StockMove, self)._get_valued_types()
        valued_types += [
            "reception",  # receptie de la furnizor fara aviz
            "reception_return",  # retur la o receptie de la funizor fara aviz
            "reception_notice",  # receptie de la furnizor cu aviz
            "reception_notice_return",  # retur receptie de la furnizor cu aviz
            "delivery",  # livrare din stoc fara aviz, aici intra si
            # dare in consum si productie
            "delivery_return",  # retur livrare din stoc fara aviz, aici
            # intra si dare in consum si productie
            "delivery_notice",  # livrare din stoc cu aviz
            "delivery_notice_return",  # retur livrare din stoc cu aviz
            "plus_inventory",  # plus inventar
            "minus_inventory",  # minus inventar
            "production",  # inregistrare produse finite prin productie
            "production_return",  # retur inregistrare produse finite
            # prin productie
        ]
        return valued_types

    # nu se mai face in mod automat evaluarea la intrare in stoc
    def _create_in_svl(self, forced_quantity=None):
        if not self.env.user.company_id.romanian_accounting:
            svl = super(StockMove, self)._create_in_svl(forced_quantity)
            return svl
        _logger.info("SVL:%s" % self.env.context.get("valued_type", ""))
        if self.env.context.get("standard"):
            svl = super(StockMove, self)._create_in_svl(forced_quantity)
        else:
            svl = self.env["stock.valuation.layer"]
        return svl

    # nu se mai face in mod automat evaluarea la iserirea din stoc
    def _create_out_svl(self, forced_quantity=None):
        if not self.env.user.company_id.romanian_accounting:
            svl = super(StockMove, self)._create_out_svl(forced_quantity)
            return svl
        _logger.info("SVL:%s" % self.env.context.get("valued_type", ""))
        if self.env.context.get("standard"):
            svl = super(StockMove, self)._create_out_svl(forced_quantity)
        else:
            svl = self.env["stock.valuation.layer"]
        return svl

    # evaluare la receptie - in mod normal nu se
    def _is_reception(self):
        """ Este receptie in stoc fara aviz"""
        it_is = (
            not self.picking_id.notice
            and self.location_id.usage == "supplier"
            and self._is_in()
        )
        return it_is

    def _create_reception_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="reception")
        return move._create_in_svl(forced_quantity)

    def _is_reception_return(self):
        """ Este un retur la o receptie in stoc fara aviz"""
        it_is = (
            not self.picking_id.notice
            and self.location_dest_id.usage == "supplier"
            and self._is_out()
        )
        return it_is

    def _create_reception_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="reception_return")
        return move._create_out_svl(forced_quantity)

    def _is_reception_notice(self):
        """ Este receptie in stoc cu aviz"""
        it_is = (
            self.picking_id.notice
            and self.location_id.usage == "supplier"
            and self._is_in()
        )
        return it_is

    def _create_reception_notice_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="reception_notice")
        return move._create_in_svl(forced_quantity)

    def _is_reception_notice_return(self):
        """ Este un retur la receptie in stoc cu aviz"""
        it_is = (
            self.picking_id.notice
            and self.location_dest_id.usage == "supplier"
            and self._is_out()
        )
        return it_is

    def _create_reception_notice_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="reception_notice_return")
        return move._create_out_svl(forced_quantity)

    def _is_delivery(self):
        """ Este livrare din stoc fara aviz"""
        return (
            not self.picking_id.notice
            and self._is_out()
            and (
                self.location_dest_id.usage == "customer"
                or self.location_dest_id.usage == "consume"
                or self.location_dest_id.usage == "usage_giving"
                or (
                    self.location_dest_id.usage == "production"
                    and not self.origin_returned_move_id
                )
            )
        )

    def _create_delivery_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery")
        return move._create_out_svl(forced_quantity)

    def _is_delivery_return(self):
        """ Este retur la o livrare din stoc fara aviz"""
        return (
            not self.picking_id.notice
            and self._is_in()
            and (
                self.location_id.usage == "customer"
                or self.location_id.usage == "consume"
                or self.location_id.usage == "usage_giving"
                or (
                    self.location_id.usage == "production"
                    and self.origin_returned_move_id
                )
            )
        )

    def _create_delivery_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery_return")
        return move._create_in_svl(forced_quantity)

    def _is_delivery_notice(self):
        """ Este livrare cu aviz"""
        return (
            self.picking_id.notice
            and self.location_dest_id.usage == "customer"
            and self._is_out()
        )

    def _create_delivery_notice_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery_notice")
        return move._create_out_svl(forced_quantity)

    def _is_delivery_notice_return(self):
        """ Este retur livrare cu aviz"""
        return (
            self.picking_id.notice
            and self.location_id.usage == "customer"
            and self._is_in()
        )

    def _create_delivery_notice_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery_notice_return")
        return move._create_in_svl(forced_quantity)

    def _is_plus_inventory(self):
        self.ensure_one()
        return (
            self.location_id.usage == "inventory"
            and self.location_dest_id.usage == "internal"
        )

    def _create_plus_inventory_svl(self, forced_quantity=None):

        move = self.with_context(standard=True, valued_type="plus_inventory")
        return move._create_in_svl(forced_quantity)

    def _is_minus_inventory(self):
        self.ensure_one()
        return (
            self.location_id.usage == "internal"
            and self.location_dest_id.usage == "inventory"
        )

    def _create_minus_inventory_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="minus_inventory")
        return move._create_out_svl(forced_quantity)

    def _is_production(self):
        """ Este inregistrare produse finite prin productie"""
        return (
            not self.picking_id.notice
            and self._is_in()
            and self.location_id.usage == "production"
            and not self.origin_returned_move_id
        )

    def _create_production_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="production")
        return move._create_in_svl(forced_quantity)

    def _is_production_return(self):
        """ Este retur inregistrare produse finite prin productie"""
        return (
            not self.picking_id.notice
            and self._is_out()
            and self.location_dest_id.usage == "production"
            and self.origin_returned_move_id
        )

    def _create_production_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="production_return")
        return move._create_in_svl(forced_quantity)

    def _is_internal_transfer(self):
        """ Este transfer intern"""
        it_is = (
            self.location_dest_id.usage == "internal"
            and self.location_id.usage == "internal"
        )
        return it_is

    def _is_usage_giving(self):
        """ Este dare in folosinta, normal sau retur"""
        it_is = (self.location_dest_id.usage == "usage_giving" and self._is_out()) or (
            self.location_id.usage == "usage_giving" and self._is_in()
        )
        return it_is

    def _prepare_common_svl_vals(self):
        vals = super(StockMove, self)._prepare_common_svl_vals()
        valued_type = self.env.context.get("valued_type")
        if valued_type:
            vals["valued_type"] = valued_type
        return vals

    def _generate_valuation_lines_data(
        self,
        partner_id,
        qty,
        debit_value,
        credit_value,
        debit_account_id,
        credit_account_id,
        description,
    ):
        # Add lines for delivery notice lines in the same move
        self.ensure_one()
        if self._is_internal_transfer():
            company = self.env.user.company_id
            valued_type = "internal_transfer"

            move = self.with_context(force_company=company.id, valued_type=valued_type)
            (
                journal_id,
                debit_account_id,
                debit_account_id,
                credit_account_id,
            ) = move._get_accounting_data_for_valuation()
        res = super(StockMove, self)._generate_valuation_lines_data(
            partner_id,
            qty,
            debit_value,
            credit_value,
            debit_account_id,
            credit_account_id,
            description,
        )
        if not self.env.user.company_id.romanian_accounting:
            return res

        # location_from = self.location_id
        # location_to = self.location_dest_id
        company_from = (
            self._is_out()
            and self.mapped("move_line_ids.location_id.company_id")
            or False
        )
        company_to = (
            self._is_in()
            and self.mapped("move_line_ids.location_dest_id.company_id")
            or False
        )
        if self._is_delivery_notice() or self._is_delivery_notice_return():
            if self._is_delivery_notice():
                # inregistrare valoare vanzare
                sale_cost = self._get_sale_amount()
                valued_type = "invoice_out_notice"
                company = company_from
            elif self._is_delivery_notice_return():
                # inregistrare retur valoare vanzare
                sale_cost = -1 * self._get_sale_amount()
                valued_type = "invoice_out_notice"
                company = company_to

            debit_value = credit_value = sale_cost
            move = self.with_context(force_company=company.id, valued_type=valued_type)
            (
                journal_id,
                debit_account_id,
                credit_account_id,
                credit_account_id,
            ) = move._get_accounting_data_for_valuation()
            debit_line_vals = {
                "name": description,
                "product_id": self.product_id.id,
                "quantity": qty,
                "product_uom_id": self.product_id.uom_id.id,
                "ref": description,
                "partner_id": partner_id,
                "debit": debit_value if debit_value > 0 else 0,
                "credit": -debit_value if debit_value < 0 else 0,
                "account_id": debit_account_id,
            }

            credit_line_vals = {
                "name": description,
                "product_id": self.product_id.id,
                "quantity": qty,
                "product_uom_id": self.product_id.uom_id.id,
                "ref": description,
                "partner_id": partner_id,
                "credit": credit_value if credit_value > 0 else 0,
                "debit": -credit_value if credit_value < 0 else 0,
                "account_id": credit_account_id,
            }

            res["notice_credit_line_vals"] = credit_line_vals
            res["notice_debit_line_vals"] = debit_line_vals
        return res

    def _account_entry_move(self, qty, description, svl_id, cost):
        """ Accounting Valuation Entries """
        if self.env.user.company_id.romanian_accounting:
            svl = self.env["stock.valuation.layer"].browse(svl_id)
            self = self.with_context(valued_type=svl.valued_type)
        res = super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)
        if self._is_usage_giving():
            # inregistrare dare in folosinta 8035
            company = self.env.user.company_id
            move = self.with_context(
                force_company=company.id, valued_type="usage_giving"
            )
            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = move._get_accounting_data_for_valuation()
            move._create_account_move_line(
                acc_src, acc_dest, journal_id, qty, description, svl_id, cost
            )
        if self._is_internal_transfer():
            # inregistrare transfer intern
            company = self.env.user.company_id
            move = self.with_context(
                force_company=company.id, valued_type="internal_transfer"
            )
            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = move._get_accounting_data_for_valuation()
            if move._is_internal_transfer():
                if move.location_id.valuation_out_account_id:
                    acc_src = move.location_id.valuation_out_account_id.id
                if move.location_dest_id.valuation_in_account_id:
                    acc_dest = move.location_dest_id.valuation_in_account_id.id
            move._create_account_move_line(
                acc_src, acc_dest, journal_id, qty, description, svl_id, cost
            )
        return res

    def _get_sale_amount(self):
        valuation_amount = 0
        sale_line = self.sale_line_id
        if sale_line:
            price_invoice = sale_line.price_subtotal / sale_line.product_uom_qty
            price_invoice = sale_line.product_uom._compute_price(
                price_invoice, self.product_uom
            )
            valuation_amount = price_invoice * abs(self.product_qty)
            company = self.location_id.company_id or self.env.user.company_id
            valuation_amount = sale_line.order_id.currency_id._convert(
                valuation_amount, company.currency_id, company, self.date
            )
        return valuation_amount

    def _create_account_move_line(
        self,
        credit_account_id,
        debit_account_id,
        journal_id,
        qty,
        description,
        svl_id,
        cost,
    ):
        # nu mai trebuie generate notele contabile de la cont de stoc la cont de stoc
        # valabil doar pentru dare in folosinta
        if (
            self.env.user.company_id.romanian_accounting
            and credit_account_id == debit_account_id
            and not self._is_usage_giving()
        ):
            return
        return super(StockMove, self)._create_account_move_line(
            credit_account_id,
            debit_account_id,
            journal_id,
            qty,
            description,
            svl_id,
            cost,
        )

    def _get_accounting_data_for_valuation(self):
        journal_id, acc_src, acc_dest, acc_valuation = super(
            StockMove, self
        )._get_accounting_data_for_valuation()
        company = self.env.user.company_id
        if not company.romanian_accounting:
            return journal_id, acc_src, acc_dest, acc_valuation
        if self.product_id.categ_id.stock_account_change:
            location_from = self.location_id
            location_to = self.location_dest_id
            valued_type = self.env.context.get("valued_type", "indefinite")
            _logger.info(valued_type)
            # in aviz si factura client se va utiliza 418
            if (
                valued_type == "invoice_out_notice"
                and location_from.property_account_income_location_id
            ):
                acc_src = acc_dest
                acc_valuation = location_from.property_account_income_location_id.id
            # la vanzare se scoate stocul pe cheltuiala
            elif valued_type in [
                "production",
                "delivery",
                "delivery_notice",
                "minus_inventory",
            ]:
                if location_from.valuation_out_account_id:
                    acc_valuation = location_from.valuation_out_account_id.id
                if location_from.property_account_expense_location_id:
                    acc_src = (
                        acc_dest
                    ) = location_from.property_account_expense_location_id.id
            elif valued_type in [
                "production_return",
                "delivery_return",
                "delivery_notice_return",
                "plus_inventory",
            ]:
                if location_to.valuation_in_account_id:
                    acc_src = acc_dest = location_to.valuation_in_account_id.id
                if location_to.property_account_expense_location_id:
                    acc_valuation = location_to.property_account_expense_location_id.id
        return journal_id, acc_src, acc_dest, acc_valuation

    def _action_done(self, cancel_backorder=False):
        # Create account move for internal transfer since  this doesn't
        # generates any new valuation layer.
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        for move in self:
            # Create account move for internal transfers
            if (
                move.env.company.romanian_accounting
                and not move.stock_valuation_layer_ids
            ):
                move._account_entry_move(
                    move.product_qty,
                    "Internal Transfer",
                    self.env["stock.valuation.layer"],
                    move._get_price_unit(),
                )
        return res
