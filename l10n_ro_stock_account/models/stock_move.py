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
            "reception",  # receptie de la furnizor fara avaiz
            "reception_return",  # retur la o receptie de la funizor fara aviz
            "delivery",  # livrare din stoc fara aviz
            "delivery_return",  # storno livrare
            "reception_notice",
            "reception_notice_return",
            "delivery_notice",
            "delivery_notice_return",
            "plus_inventory",
            "minus_inventory",
        ]
        return valued_types

    # nu se mai face in mod automat evaluarea la intrare in stoc
    def _create_in_svl(self, forced_quantity=None):
        _logger.info("SVL:%s" % self.env.context.get("valued_type", ""))
        if self.env.context.get("standard"):
            svl = super(StockMove, self)._create_in_svl(forced_quantity)
        else:
            svl = self.env["stock.valuation.layer"]
        return svl

    # nu se mai face in mod automat evaluarea la iserirea din stoc
    def _create_out_svl(self, forced_quantity=None):
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
            and self.location_dest_id.usage == "customer"
            and self._is_out()
        )

    def _create_delivery_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery")
        return move._create_out_svl(forced_quantity)

    def _is_delivery_return(self):
        """ Este retur la o livrare din stoc fara aviz"""
        return (
            not self.picking_id.notice
            and self.location_id.usage == "customer"
            and self._is_in()
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
        """ Este livrare cu aviz"""
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

    def _prepare_common_svl_vals(self):
        vals = super(StockMove, self)._prepare_common_svl_vals()
        valued_type = self.env.context.get("valued_type")
        if valued_type:
            vals["valued_type"] = valued_type
        return vals

    def _account_entry_move(self, qty, description, svl_id, cost):
        """ Accounting Valuation Entries """

        svl = self.env["stock.valuation.layer"].browse(svl_id)
        self = self.with_context(valued_type=svl.valued_type)

        res = super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)

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

        if self._is_delivery_notice():
            # inregistrare valoare vanzare
            sale_cost = self._get_sale_amount()
            move = self.with_context(
                force_company=company_from.id, valued_type="invoice_out_notice"
            )

            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = move._get_accounting_data_for_valuation()
            move._create_account_move_line(
                acc_valuation, acc_dest, journal_id, qty, description, svl_id, sale_cost
            )
        if self._is_delivery_notice_return():
            # inregistrare valoare vanzare
            sale_cost = -1 * self._get_sale_amount()
            move = self.with_context(
                force_company=company_to.id, valued_type="invoice_out_notice"
            )

            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = move._get_accounting_data_for_valuation()
            move._create_account_move_line(
                acc_dest, acc_valuation, journal_id, qty, description, svl_id, sale_cost
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
        if credit_account_id == debit_account_id:
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
