# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, models
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "l10n.ro.mixin"]

    @api.model
    def _get_valued_types(self):
        valued_types = super(StockMove, self)._get_valued_types()
        if self.filtered("is_l10n_ro_record"):
            valued_types += [
                "reception",  # receptie de la furnizor fara aviz
                "reception_return",  # retur la o receptie de la funizor fara aviz
                "delivery",  # livrare din stoc fara aviz
                "delivery_return",  # storno livrare
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

    def _get_price_unit(self):
        # La fel ca in baza, doar ca nu mai face rotunjire de price_unit
        self.ensure_one()
        if self.is_l10n_ro_record:
            price_unit = self.price_unit
            precision = self.env["decimal.precision"].precision_get("Product Price")
            # If the move is a return, use the original move's price unit.
            if (
                self.origin_returned_move_id
                and self.origin_returned_move_id.sudo().stock_valuation_layer_ids
            ):
                layers = self.origin_returned_move_id.sudo().stock_valuation_layer_ids
                quantity = sum(layers.mapped("quantity"))
                return (
                    sum(layers.mapped("value")) / quantity
                    if not float_is_zero(
                        quantity, precision_rounding=layers.uom_id.rounding
                    )
                    else 0
                )
            return (
                price_unit
                if not float_is_zero(price_unit, precision)
                or self._should_force_price_unit()
                else self.product_id.standard_price
            )
        else:
            return super()._get_price_unit()

    # nu se mai face in mod automat evaluarea la intrare in stoc
    def _create_in_svl(self, forced_quantity=None):
        _logger.debug("SVL:%s" % self.env.context.get("valued_type", ""))
        svls = self.env["stock.valuation.layer"]
        l10n_ro_records = self.filtered("is_l10n_ro_record")
        if self - l10n_ro_records:
            svls = super(StockMove, self - l10n_ro_records)._create_in_svl(
                forced_quantity
            )
        if l10n_ro_records and self.env.context.get("standard"):
            # For Romania, create a valuation layer for each stock move line
            for move in l10n_ro_records:
                move = move.with_company(move.company_id)
                valued_move_lines = move._get_in_move_lines()
                for valued_move_line in valued_move_lines:
                    move = move.with_context(stock_move_line_id=valued_move_line)
                    valued_quantity = valued_move_line.product_uom_id._compute_quantity(
                        valued_move_line.qty_done, move.product_id.uom_id
                    )
                    origin_unit_cost = None
                    tracking = []
                    if (
                        move.origin_returned_move_id
                        and move.origin_returned_move_id.sudo().stock_valuation_layer_ids
                    ):
                        origin_domain = move.product_id._l10n_ro_prepare_domain_fifo(
                            move.company_id,
                            [("product_id", "=", valued_move_line.product_id.id)],
                        )
                        origin_domain = [
                            (
                                "stock_move_line_id",
                                "in",
                                move.origin_returned_move_id._get_in_move_lines().ids,
                            )
                        ] + origin_domain
                        origin_svls = move._l10n_ro_filter_svl_on_move_line(
                            origin_domain
                        )
                        if origin_svls:
                            origin_unit_cost = origin_svls[0].unit_cost
                            tracking = [
                                (
                                    origin_svls[0].id,
                                    valued_quantity,
                                    origin_unit_cost * valued_quantity,
                                )
                            ]
                    unit_cost = abs(
                        origin_unit_cost or move._get_price_unit()
                    )  # May be negative (i.e. decrease an out move).
                    if move.product_id.cost_method == "standard":
                        unit_cost = move.product_id.standard_price
                    svl_vals = move.product_id._prepare_in_svl_vals(
                        forced_quantity or valued_quantity, unit_cost
                    )
                    svl_vals.update(move._prepare_common_svl_vals())
                    svl_vals.update(
                        {
                            "l10n_ro_stock_move_line_id": valued_move_line.id,
                            "tracking": tracking,
                        }
                    )
                    if forced_quantity:
                        svl_vals["description"] = (
                            "Correction of %s (modification of past move)"
                            % move.picking_id.name
                            or move.name
                        )
                    svls |= self._l10n_ro_create_track_svl([svl_vals])
        return svls

    # nu se mai face in mod automat evaluarea la iserirea din stoc
    def _create_out_svl(self, forced_quantity=None):
        _logger.debug("SVL:%s" % self.env.context.get("valued_type", ""))
        svls = self.env["stock.valuation.layer"]
        l10n_ro_records = self.filtered("is_l10n_ro_record")
        if self - l10n_ro_records:
            svls = super(StockMove, self - l10n_ro_records)._create_out_svl(
                forced_quantity
            )
        if l10n_ro_records and self.env.context.get("standard"):
            # For Romania get a list of valuation layers, to keep traceability
            # for each incoming price
            for move in self:
                move = move.with_company(move.company_id)
                valued_move_lines = move._get_out_move_lines()
                for valued_move_line in valued_move_lines:
                    valued_move_line = valued_move_line.with_context(
                        stock_move_line_id=valued_move_line
                    )
                    move = move.with_context(stock_move_line_id=valued_move_line)
                    valued_quantity = valued_move_line.product_uom_id._compute_quantity(
                        valued_move_line.qty_done, move.product_id.uom_id
                    )
                    if float_is_zero(
                        forced_quantity or valued_quantity,
                        precision_rounding=move.product_id.uom_id.rounding,
                    ):
                        continue
                    svl_vals_list = valued_move_line.product_id._prepare_out_svl_vals(
                        forced_quantity or valued_quantity,
                        valued_move_line.company_id,
                    )
                    for svl_vals in svl_vals_list:
                        svl_vals.update(move._prepare_common_svl_vals())
                        svl_vals.update(
                            {
                                "l10n_ro_stock_move_line_id": valued_move_line.id,
                            }
                        )
                        if forced_quantity:
                            svl_vals["description"] = (
                                "Correction of %s (modification of past move)"
                                % valued_move_line.picking_id.name
                                or valued_move_line.name
                            )
                        svl_vals["description"] += svl_vals.pop(
                            "rounding_adjustment", ""
                        )
                        svls |= move._l10n_ro_create_track_svl([svl_vals])
        return svls

    def _is_returned(self, valued_type):
        """Este tot timpul False deoarece noi tratam fiecare caz in parte
        de retur si fxam conturile"""
        if not self.is_l10n_ro_record:
            return super()._is_returned(valued_type)
        return False

    # evaluare la receptie - in mod normal nu se
    def _is_reception(self):
        """Este receptie in stoc fara aviz"""
        it_is = (
            self.is_l10n_ro_record
            and self.location_id.usage == "supplier"
            and self._is_in()
        )
        return it_is

    def _create_reception_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="reception")
        return move._create_in_svl(forced_quantity)

    def _is_reception_return(self):
        """Este un retur la o receptie in stoc fara aviz"""
        it_is = (
            self.is_l10n_ro_record
            and self.location_dest_id.usage == "supplier"
            and self._is_out()
        )
        return it_is

    def _create_reception_return_svl(self, forced_quantity=None):
        svl = self.env["stock.valuation.layer"]
        for move in self:
            move = move.with_context(standard=True, valued_type="reception_return")
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
        return (
            self.is_l10n_ro_record
            and self.location_dest_id.usage == "customer"
            and self._is_out()
        )

    def _create_delivery_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery")
        return move._create_out_svl(forced_quantity)

    def _is_delivery_return(self):
        """Este retur la o livrare din stoc fara aviz"""
        it_is = (
            self.is_l10n_ro_record
            and self.location_id.usage == "customer"
            and self._is_in()
        )
        return it_is

    def _create_delivery_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="delivery_return")
        return move._create_in_svl(forced_quantity)

    def _is_plus_inventory(self):
        it_is = (
            self.is_l10n_ro_record
            and self.location_id.usage == "inventory"
            and self.location_dest_id.usage == "internal"
        )
        return it_is

    def _create_plus_inventory_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="plus_inventory")
        return move._create_in_svl(forced_quantity)

    def _is_minus_inventory(self):
        it_is = (
            self.is_l10n_ro_record
            and self.location_id.usage == "internal"
            and self.location_dest_id.usage == "inventory"
        )
        return it_is

    def _create_minus_inventory_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="minus_inventory")
        return move._create_out_svl(forced_quantity)

    def _is_production(self):
        """Este inregistrare intrare produse finite prin productie"""
        it_is = (
            self.is_l10n_ro_record
            and self._is_in()
            and self.location_id.usage == "production"
        )
        return it_is

    def _create_production_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="production")
        return move._create_in_svl(forced_quantity)

    def _is_production_return(self):
        """Este retur inregistrare produse finite prin productie"""
        it_is = (
            self.company_id.l10n_ro_accounting
            and self._is_out()
            and self.location_dest_id.usage == "production"
            and self.origin_returned_move_id
        )
        return it_is

    def _create_production_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="production_return")
        if (
            move.origin_returned_move_id
            and move.origin_returned_move_id.sudo().stock_valuation_layer_ids
        ):
            move = move.with_context(
                origin_return_candidates=move.origin_returned_move_id.sudo()
                .stock_valuation_layer_ids.filtered(lambda sv: sv.remaining_qty > 0)
                .ids
            )

        return move._create_out_svl(forced_quantity)

    def _is_consumption(self):
        """Este un conusm de materiale in productie"""
        it_is = (
            self.is_l10n_ro_record
            and self._is_out()
            and self.location_dest_id.usage in ("consume", "production")
            and not self.origin_returned_move_id
        )
        return it_is

    def _create_consumption_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="consumption")
        return move._create_out_svl(forced_quantity)

    def _is_consumption_return(self):
        """Este un conusm de materiale in productie"""
        it_is = (
            self.is_l10n_ro_record
            and self._is_in()
            and self.location_id.usage in ("consume", "production")
            and self.origin_returned_move_id
        )
        return it_is

    def _create_consumption_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="consumption_return")
        return move._create_in_svl(forced_quantity)

    def _is_internal_transfer(self):
        """Este transfer intern"""
        it_is = (
            self.is_l10n_ro_record
            and self.location_dest_id.usage == "internal"
            and self.location_id.usage == "internal"
        )
        return it_is

    # cred ca este mai bine sa generam doua svl - o intrare si o iesire
    def _create_internal_transfer_svl(self, forced_quantity=None):
        svls = self.env["stock.valuation.layer"]
        for move in self:
            move = move.with_context(standard=True, valued_type="internal_transfer")
            move = move.with_company(move.company_id.id)

            valued_move_lines = move.move_line_ids
            for valued_move_line in valued_move_lines:
                move = move.with_context(stock_move_line_id=valued_move_line)
                valued_quantity = valued_move_line.product_uom_id._compute_quantity(
                    valued_move_line.qty_done, move.product_id.uom_id
                )
                if float_is_zero(
                    forced_quantity or valued_quantity,
                    precision_rounding=move.product_id.uom_id.rounding,
                ):
                    continue
                svl_vals_list = move.product_id._prepare_out_svl_vals(
                    forced_quantity or valued_quantity, move.company_id
                )
                for svl_vals in svl_vals_list:
                    svl_vals.update(move._prepare_common_svl_vals())
                    if forced_quantity:
                        svl_vals["description"] = (
                            "Correction of %s (modification of past move)"
                            % move.picking_id.name
                            or move.name
                        )
                    svl_vals["description"] += svl_vals.pop("rounding_adjustment", "")
                    svls |= self._l10n_ro_create_track_svl([svl_vals])

                    new_svl_vals = svl_vals.copy()
                    new_svl_vals.update(
                        {
                            "quantity": abs(svl_vals.get("quantity", 0)),
                            "remaining_qty": abs(svl_vals.get("quantity", 0)),
                            "unit_cost": abs(svl_vals.get("unit_cost", 0)),
                            "value": abs(svl_vals.get("value", 0)),
                            "remaining_value": abs(svl_vals.get("value", 0)),
                            "tracking": [
                                (
                                    svls[-1].id,
                                    abs(svl_vals.get("quantity", 0)),
                                    abs(svl_vals.get("value", 0)),
                                )
                            ],
                        }
                    )
                    svls |= self._l10n_ro_create_track_svl([new_svl_vals])
        return svls

    def _is_usage_giving(self):
        """Este dare in folosinta"""
        it_is = (
            self.is_l10n_ro_record
            and self.location_dest_id.usage == "usage_giving"
            and self._is_out()
        )

        return it_is

    def _create_usage_giving_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="usage_giving")
        return move._create_out_svl(forced_quantity)

    def _is_usage_giving_return(self):
        """Este return dare in folosinta"""
        it_is = (
            self.is_l10n_ro_record
            and self.location_id.usage == "usage_giving"
            and self._is_in()
        )
        return it_is

    def _create_usage_giving_return_svl(self, forced_quantity=None):
        move = self.with_context(standard=True, valued_type="usage_giving_return")
        return move._create_in_svl(forced_quantity)

    def _prepare_common_svl_vals(self):
        vals = super(StockMove, self)._prepare_common_svl_vals()
        if self.is_l10n_ro_record:
            valued_type = self.env.context.get("valued_type")
            if valued_type:
                vals["l10n_ro_valued_type"] = valued_type
            vals[
                "l10n_ro_account_id"
            ] = self.product_id.categ_id.property_stock_valuation_account_id.id
        return vals

    def _create_dropshipped_svl(self, forced_quantity=None):
        valued_type = "dropshipped"
        self = self.with_context(valued_type=valued_type)
        return super(StockMove, self)._create_dropshipped_svl(forced_quantity)

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
        """Accounting Valuation Entries"""
        if self.is_l10n_ro_record:
            svl = self.env["stock.valuation.layer"].browse(svl_id)
            company = self._get_company(svl)
            self = company and self.with_company(company.id) or self
            if company and company.l10n_ro_accounting:
                self = self.with_context(
                    valued_type=svl.l10n_ro_valued_type, standard=True
                )

        res = super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)

        if self.is_l10n_ro_record:
            self._romanian_account_entry_move(qty, description, svl_id, cost)

        return res

    def _romanian_account_entry_move(self, qty, description, svl_id, cost):
        location_from = self.location_id
        location_to = self.location_dest_id
        svl = self.env["stock.valuation.layer"]
        if self._is_usage_giving() or self._is_consumption():
            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = self._get_accounting_data_for_valuation()
            acc_valuation_rec = self.env["account.account"].browse(acc_valuation)
            if acc_valuation_rec and acc_valuation_rec.l10n_ro_stock_consume_account_id:
                acc_valuation = acc_valuation_rec.l10n_ro_stock_consume_account_id.id
            if acc_src != acc_valuation:
                self._create_account_move_line(
                    acc_valuation, acc_src, journal_id, qty, description, svl, cost
                )
        if self._is_usage_giving_return() or self._is_consumption_return():
            (
                journal_id,
                acc_src,
                acc_dest,
                acc_valuation,
            ) = self._get_accounting_data_for_valuation()
            acc_valuation_rec = self.env["account.account"].browse(acc_valuation)
            if acc_valuation_rec and acc_valuation_rec.l10n_ro_stock_consume_account_id:
                acc_valuation = acc_valuation_rec.l10n_ro_stock_consume_account_id.id
            if acc_dest != acc_valuation:
                self._create_account_move_line(
                    acc_dest, acc_valuation, journal_id, qty, description, svl, cost
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
            if location_to.l10n_ro_property_stock_valuation_account_id and cost < 0:
                move._create_account_move_line(
                    acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost
                )
            if location_from.l10n_ro_property_stock_valuation_account_id and cost > 0:
                move._create_account_move_line(
                    acc_src, acc_valuation, journal_id, qty, description, svl_id, cost
                )

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
            self.is_l10n_ro_record
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
        valued_type = self.env.context.get("valued_type", "indefinite")
        if (
            self.is_l10n_ro_record
            and self.product_id.categ_id.l10n_ro_stock_account_change
        ):
            location_from = self.location_id
            location_to = self.location_dest_id
            # produsele din aceasta locatia folosesc pentru evaluare contul
            if location_to.l10n_ro_property_stock_valuation_account_id:
                # in cazul unui transfer intern se va face contare dintre
                # contul de stoc si contul din locatie
                if valued_type == "internal_transfer":
                    acc_dest = (
                        location_to.l10n_ro_property_stock_valuation_account_id.id
                    )
                else:
                    acc_valuation = (
                        location_to.l10n_ro_property_stock_valuation_account_id.id
                    )
                if valued_type == "reception":
                    acc_src = acc_valuation

            # produsele din aceasta locatia folosesc pentru evaluare contul
            if location_from.l10n_ro_property_stock_valuation_account_id:
                # in cazul unui transfer intern se va face contare dintre
                # contul de stoc si contul din locatie
                if valued_type == "internal_transfer":
                    acc_src = (
                        location_from.l10n_ro_property_stock_valuation_account_id.id
                    )
                else:
                    acc_valuation = (
                        location_from.l10n_ro_property_stock_valuation_account_id.id
                    )
                    acc_src = (
                        location_from.l10n_ro_property_stock_valuation_account_id.id
                    )
            # in cazul transferului intern se va face o singura nota
            if (
                location_from.l10n_ro_property_stock_valuation_account_id
                and location_to.l10n_ro_property_stock_valuation_account_id
            ):
                acc_valuation = (
                    location_from.l10n_ro_property_stock_valuation_account_id.id
                )
            # in Romania iesirea din stoc de face de regula pe contul de cheltuiala
            if valued_type in [
                "delivery",
                "consumption",
                "usage_giving",
                "production_return",
                "minus_inventory",
            ]:
                acc_dest = (
                    location_from.l10n_ro_property_account_expense_location_id.id
                    or acc_dest
                )
            elif valued_type in [
                "production",
                "delivery_return",
                "consumption_return",
                "usage_giving_return",
                "plus_inventory",
            ]:
                acc_src = (
                    location_to.l10n_ro_property_account_expense_location_id.id
                    or acc_src
                )

        if self.is_l10n_ro_record and valued_type in (
            "consumption",
            "usage_giving",
        ):
            acc_dest_rec = self.env["account.account"].browse(acc_dest)
            if acc_dest_rec and acc_dest_rec.l10n_ro_stock_consume_account_id:
                acc_dest = acc_dest_rec.l10n_ro_stock_consume_account_id.id
            acc_valuation_rec = self.env["account.account"].browse(acc_valuation)
            if acc_valuation_rec and acc_valuation_rec.l10n_ro_stock_consume_account_id:
                acc_valuation = acc_valuation_rec.l10n_ro_stock_consume_account_id.id
        if self.is_l10n_ro_record and valued_type in (
            "consumption_return",
            "usage_giving_return",
        ):
            acc_src_rec = self.env["account.account"].browse(acc_src)
            if acc_src_rec and acc_src_rec.l10n_ro_stock_consume_account_id:
                acc_src = acc_src_rec.l10n_ro_stock_consume_account_id.id
            acc_valuation_rec = self.env["account.account"].browse(acc_valuation)
            if acc_valuation_rec and acc_valuation_rec.l10n_ro_stock_consume_account_id:
                acc_valuation = acc_valuation_rec.l10n_ro_stock_consume_account_id.id
        return journal_id, acc_src, acc_dest, acc_valuation

    def _l10n_ro_filter_svl_on_move_line(self, domain):
        origin_svls = self.env["stock.valuation.layer"].search(domain)
        return origin_svls

    def _l10n_ro_create_track_svl(self, value_list, **kwargs):
        sudo_svl = self.env["stock.valuation.layer"].sudo()

        for _index, value in enumerate(value_list):
            svl_value = sudo_svl._l10n_ro_pre_process_value(
                value
            )  # eliminam datele de tracking, filtram valorile SVL
            new_svl = sudo_svl.create(svl_value)
            new_svl._l10n_ro_post_process(value)  # executam post create pentru tracking
            sudo_svl |= new_svl
        return sudo_svl
