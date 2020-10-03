# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, models
from odoo.tools import float_is_zero

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
            "delivery",  # livrare din stoc fara aviz
            "delivery_return",  # storno livrare
            "delivery_notice",
            "delivery_notice_return",
            "plus_inventory",
            "minus_inventory",
            "consumption",  # consum in productie
            "consumption_return",  # storno consum produse
            "production",  # inregistrare produse finite/semifabricate prin productie
            "production_return",  # storno productie
            "internal_transfer",  # transfer intern
            "usage_giving",
            "usage_giving_return",
        ]
        return valued_types

    # nu se mai face in mod automat evaluarea la intrare in stoc
    def _create_in_svl(self, forced_quantity=None):
        _logger.info("SVL:%s" % self.env.context.get("valued_type", ""))
        if self.env.context.get("standard") or not self.company_id.romanian_accounting:
            svl = super(StockMove, self)._create_in_svl(forced_quantity)
        else:
            svl = self.env["stock.valuation.layer"]
        return svl

    # nu se mai face in mod automat evaluarea la iserirea din stoc
    def _create_out_svl(self, forced_quantity=None):
        _logger.info("SVL:%s" % self.env.context.get("valued_type", ""))
        if self.env.context.get("standard") or not self.company_id.romanian_accounting:
            svl = super(StockMove, self)._create_out_svl(forced_quantity)
        else:
            svl = self.env["stock.valuation.layer"]
        return svl

    # evaluare la receptie - in mod normal nu se
    def _is_reception(self):
        """ Este receptie in stoc fara aviz"""
        it_is = (
            self.company_id.romanian_accounting
            and not self.picking_id.notice
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
            self.company_id.romanian_accounting
            and not self.picking_id.notice
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
            self.company_id.romanian_accounting
            and self.picking_id.notice
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
            self.company_id.romanian_accounting
            and self.picking_id.notice
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
            self.company_id.romanian_accounting
            and not self.picking_id.notice
            and self.location_dest_id.usage == "customer"
            and self._is_out()
        )

    def _create_delivery_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery")
        return move._create_out_svl(forced_quantity)

    def _is_delivery_return(self):
        """ Este retur la o livrare din stoc fara aviz"""
        it_is = (
            self.company_id.romanian_accounting
            and not self.picking_id.notice
            and self.location_id.usage == "customer"
            and self._is_in()
        )
        return it_is

    def _create_delivery_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery_return")
        return move._create_in_svl(forced_quantity)

    def _is_delivery_notice(self):
        """ Este livrare cu aviz"""
        it_is = (
            self.company_id.romanian_accounting
            and self.picking_id.notice
            and self.location_dest_id.usage == "customer"
            and self._is_out()
        )
        return it_is

    def _create_delivery_notice_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery_notice")
        return move._create_out_svl(forced_quantity)

    def _is_delivery_notice_return(self):
        """ Este retur livrare cu aviz"""
        it_is = (
            self.company_id.romanian_accounting
            and self.picking_id.notice
            and self.location_id.usage == "customer"
            and self._is_in()
        )
        return it_is

    def _create_delivery_notice_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery_notice_return")
        return move._create_in_svl(forced_quantity)

    def _is_plus_inventory(self):
        it_is = (
            self.company_id.romanian_accounting
            and self.location_id.usage == "inventory"
            and self.location_dest_id.usage == "internal"
        )
        return it_is

    def _create_plus_inventory_svl(self, forced_quantity=None):

        move = self.with_context(standard=True, valued_type="plus_inventory")
        return move._create_in_svl(forced_quantity)

    def _is_minus_inventory(self):
        it_is = (
            self.company_id.romanian_accounting
            and self.location_id.usage == "internal"
            and self.location_dest_id.usage == "inventory"
        )
        return it_is

    def _create_minus_inventory_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="minus_inventory")
        return move._create_out_svl(forced_quantity)

    def _is_production(self):
        """ Este inregistrare intrare produse finite prin productie"""
        it_is = (
            self.company_id.romanian_accounting
            and self._is_in()
            and self.location_id.usage == "production"
        )
        return it_is

    def _create_production_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="production")
        return move._create_in_svl(forced_quantity)

    def _is_production_return(self):
        """ Este retur inregistrare produse finite prin productie"""
        it_is = (
            self.company_id.romanian_accounting
            and self._is_out()
            and self.location_dest_id.usage == "production"
        )
        return it_is

    def _create_production_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="production_return")
        return move._create_out_svl(forced_quantity)

    def _is_consumption(self):
        """ Este un conusm de materiale in productie"""
        it_is = (
            self.company_id.romanian_accounting
            and self._is_out()
            and self.location_dest_id.usage == "consume"
            and not self.origin_returned_move_id
        )
        return it_is

    def _create_consumption_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="consumption")
        return move._create_out_svl(forced_quantity)

    def _is_consumption_return(self):
        """ Este un conusm de materiale in productie"""
        it_is = (
            self.company_id.romanian_accounting
            and self._is_in()
            and self.location_id.usage == "consume"
            and self.origin_returned_move_id
        )
        return it_is

    def _create_consumption_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="consumption_return")
        return move._create_in_svl(forced_quantity)

    def _is_internal_transfer(self):
        """ Este transfer intern"""
        it_is = (
            self.company_id.romanian_accounting
            and self.location_dest_id.usage == "internal"
            and self.location_id.usage == "internal"
        )
        return it_is

    # cred ca este mai bine sa generam doua svl - o intrare si o iesire
    def _create_internal_transfer_svl(self, forced_quantity=None):
        svl_vals_list = []
        for move in self.with_context(standard=True, valued_type="internal_transfer"):
            move = move.with_context(force_company=move.company_id.id)

            valued_move_lines = move.move_line_ids
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(
                    valued_move_line.qty_done, move.product_id.uom_id
                )
            if float_is_zero(
                forced_quantity or valued_quantity,
                precision_rounding=move.product_id.uom_id.rounding,
            ):
                continue
            svl_vals = move.product_id._prepare_out_svl_vals(
                forced_quantity or valued_quantity, move.company_id
            )
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals["description"] = (
                    "Correction of %s (modification of past move)"
                    % move.picking_id.name
                    or move.name
                )
            svl_vals_list.append(svl_vals)

        for move in self.with_context(standard=True, valued_type="internal_transfer"):
            move = move.with_context(force_company=move.company_id.id)
            valued_move_lines = move.move_line_ids
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(
                    valued_move_line.qty_done, move.product_id.uom_id
                )
            unit_cost = abs(
                move._get_price_unit()
            )  # May be negative (i.e. decrease an out move).
            if move.product_id.cost_method == "standard":
                unit_cost = move.product_id.standard_price
            svl_vals = move.product_id._prepare_in_svl_vals(
                forced_quantity or valued_quantity, unit_cost
            )
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals["description"] = (
                    "Correction of %s (modification of past move)"
                    % move.picking_id.name
                    or move.name
                )
            svl_vals_list.append(svl_vals)

        return self.env["stock.valuation.layer"].sudo().create(svl_vals_list)

    def _is_usage_giving(self):
        """ Este dare in folosinta"""
        it_is = (
            self.company_id.romanian_accounting
            and self.location_dest_id.usage == "usage_giving"
            and self._is_out()
        )

        return it_is

    def _create_usage_giving_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="usage_giving")
        return move._create_out_svl(forced_quantity)

    def _is_usage_giving_return(self):
        """ Este return dare in folosinta"""
        it_is = (
            self.company_id.romanian_accounting
            and self.location_id.usage == "usage_giving"
            and self._is_in()
        )
        return it_is

    def _create_usage_giving_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="usage_giving_return")
        return move._create_in_svl(forced_quantity)

    def _prepare_common_svl_vals(self):
        vals = super(StockMove, self)._prepare_common_svl_vals()
        valued_type = self.env.context.get("valued_type")
        if valued_type:
            vals["valued_type"] = valued_type
        return vals

    def _get_company(self, svl):
        self.ensure_one()
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

        if self._is_in():
            return company_to

        if self._is_out():
            return company_from

        return self.env.company

    def _account_entry_move(self, qty, description, svl_id, cost):
        """ Accounting Valuation Entries """
        svl = self.env["stock.valuation.layer"].browse(svl_id)
        company = self._get_company(svl)
        self = company and self.with_context(force_company=company.id) or self
        if company and company.romanian_accounting:
            self = self.with_context(
                valued_type=svl.valued_type, is_romanian_accounting=True
            )

        res = super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)

        if company and company.romanian_accounting:
            self._romanian_account_entry_move(qty, description, svl_id, cost)

        return res

    def _romanian_account_entry_move(self, qty, description, svl_id, cost):
        location_from = self.location_id
        location_to = self.location_dest_id
        svl = self.env["stock.valuation.layer"]
        if self._is_delivery_notice():
            # inregistrare valoare vanzare
            sale_cost = self._get_sale_amount()
            move = self.with_context(valued_type="invoice_out_notice")

            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = move._get_accounting_data_for_valuation()
            move._create_account_move_line(
                acc_valuation, acc_dest, journal_id, qty, description, svl, sale_cost
            )

        if self._is_delivery_notice_return():
            # inregistrare valoare vanzare
            sale_cost = -1 * self._get_sale_amount()
            move = self.with_context(valued_type="invoice_out_notice")

            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = move._get_accounting_data_for_valuation()
            move._create_account_move_line(
                acc_dest, acc_valuation, journal_id, qty, description, svl_id, sale_cost
            )

        if self._is_usage_giving() or self._is_usage_giving_return():
            # inregistrare dare in folosinta 8035
            move = self.with_context(valued_type="usage_giving_secondary")
            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = move._get_accounting_data_for_valuation()
            move._create_account_move_line(
                acc_src, acc_dest, journal_id, qty, description, svl, cost
            )

        if self._is_internal_transfer():
            move = self.with_context(valued_type="internal_transfer")
            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = move._get_accounting_data_for_valuation()
            if location_to.property_stock_valuation_account_id and cost < 0:
                move._create_account_move_line(
                    acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost
                )
            if location_from.property_stock_valuation_account_id and cost > 0:
                move._create_account_move_line(
                    acc_src, acc_valuation, journal_id, qty, description, svl_id, cost
                )

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
            self.company_id.romanian_accounting
            and credit_account_id == debit_account_id
            and not self._is_usage_giving()
            and not self._is_usage_giving_return()
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
        if (
            self.company_id.romanian_accounting
            and self.product_id.categ_id.stock_account_change
        ):
            location_from = self.location_id
            location_to = self.location_dest_id
            valued_type = self.env.context.get("valued_type", "indefinite")
            # produsele din aceasta locatia folosesc pentru evaluare contul
            if location_to.property_stock_valuation_account_id:
                # in cazul unui transfer intern se va face contare dintre
                # contul de stoc si contul din locatie
                if valued_type == "internal_transfer":
                    acc_dest = location_to.property_stock_valuation_account_id.id
                else:
                    acc_valuation = location_to.property_stock_valuation_account_id.id
                if valued_type == "reception":
                    acc_src = acc_valuation

            # produsele din aceasta locatia folosesc pentru evaluare contul
            if location_from.property_stock_valuation_account_id:
                # in cazul unui transfer intern se va face contare dintre
                # contul de stoc si contul din locatie
                if valued_type == "internal_transfer":
                    acc_src = location_from.property_stock_valuation_account_id.id
                else:
                    acc_valuation = location_from.property_stock_valuation_account_id.id

            # in nir si factura se ca utiliza 408
            if valued_type == "invoice_in_notice":
                if location_to.property_account_expense_location_id:
                    acc_dest = (
                        acc_valuation
                    ) = location_to.property_account_expense_location_id.id
                # if location_to.property_account_expense_location_id:
                #     acc_dest = (
                #         acc_valuation
                #     ) = location_to.property_account_expense_location_id.id
            elif valued_type == "invoice_out_notice":
                if location_to.property_account_income_location_id:
                    acc_valuation = acc_dest
                    acc_dest = location_to.property_account_income_location_id.id
                if location_from.property_account_income_location_id:
                    acc_valuation = location_from.property_account_income_location_id.id

            # in Romania iesirea din stoc de face de regula pe contul de cheltuiala
            elif valued_type in [
                "delivery",
                "delivery_notice",
                "consumption",
                "usage_giving",
                "production_return",
                "minus_inventory",
            ]:
                acc_dest = (
                    location_from.property_account_expense_location_id.id or acc_dest
                )
            elif valued_type in [
                "production",
                "delivery_return",
                "delivery_notice_return",
                "consumption_return",
                "usage_giving_return",
                "plus_inventory",
            ]:
                acc_src = location_to.property_account_expense_location_id.id or acc_src
        return journal_id, acc_src, acc_dest, acc_valuation
