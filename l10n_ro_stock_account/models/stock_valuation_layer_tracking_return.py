# Copyright (C) 2022 Dakai Soft
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    # pachet tracking cu retururi pe svl orig
    l10n_ro_track_return_ids = fields.One2many(
        "l10n.ro.stock.valuation.layer.tracking", "svl_return_id"
    )
    # compute set retururi pe svl orig.
    l10n_ro_svl_return_ids = fields.Many2many(
        "stock.valuation.layer", compute="_compute_l10n_ro_svl_tracking_return"
    )
    l10n_ro_qty_returned = fields.Float(compute="_compute_returned_qty", store=True)

    @api.depends("l10n_ro_track_return_ids.svl_dest_id")
    def _compute_l10n_ro_svl_tracking_return(self):
        for s in self:
            s.l10n_ro_svl_return_ids = s.l10n_ro_track_return_ids.mapped("svl_dest_id")

    @api.depends("l10n_ro_track_return_ids.quantity")
    def _compute_returned_qty(self):
        for s in self:
            s.l10n_ro_qty_returned = sum(s.l10n_ro_track_return_ids.mapped("quantity"))

    def _check_return_permision(self):
        qty_needed = self.quantity
        target_qty = sum(self.l10n_ro_svl_return_ids.mapped("remaining_qty"))
        available = sum(self.l10n_ro_svl_dest_ids.mapped("l10n_ro_qty_returned"))
        if self.l10n_ro_location_dest_id.usage in ["consume"]:
            return (False, "Can not roll back consumed products %s", self)
        elif abs(qty_needed) in [
            abs(target_qty),
            abs(available),
            self.remaining_qty,
            (available + self.remaining_qty),
            (target_qty + self.remaining_qty),
        ]:
            return (True, None, self)
        else:
            return (
                False,
                "First you must to reverse %s %s"
                % (
                    self.stock_move_id.display_name,
                    self.getDocMove(move=self.stock_move_id),
                ),
                self,
            )
        return (None, None, self)

    def _colector_return_available(self, down_stream=None):
        if "internal_transfer" in self.l10n_ro_valued_type and self.quantity < 0:
            self = self.l10n_ro_svl_dest_ids
        if not down_stream:
            down_stream = []

        bolean_check, message, svl = self._check_return_permision()

        if bolean_check in [True, False]:
            down_stream += [(bolean_check, message, svl)]
        if bolean_check:
            return down_stream[:-1]
        for svl_dest in self.l10n_ro_svl_track_dest_ids.mapped("svl_dest_id"):
            down_stream = svl_dest._colector_return_available(down_stream=down_stream)
        return down_stream

    def getDocMove(self, move=None):
        if not move:
            self.ensure_one()
            move = self
        name = ""
        if move.picking_id:
            name = move.picking_id.display_name
        return name

    def check_return_available(self, svl_check=None):
        if not svl_check:
            self.ensure_one()
            svl_check = self
        down_stream = svl_check._colector_return_available()
        up_stream = down_stream[:]
        up_stream.reverse()
        if svl_check.l10n_ro_location_dest_id.usage in ["customer"]:
            return True, None
        for entry in up_stream:
            if entry[0] in [False]:
                return False, entry[1]
        # raise
        return True, None


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _prepare_out_svl_vals(self, quantity, company):
        # FOr Romania, prepare a svl vals list for each svl reserved
        if not self.is_l10n_ro_record:
            return super(ProductProduct, self)._prepare_out_svl_vals(quantity, company)
        self.ensure_one()
        if self._context.get("origin_return_candidates", None):
            return self._l10n_ro_prepare_out_svls_vals_return(
                quantity, company, self._context.get("origin_return_candidates")
            )
        return super(ProductProduct, self)._prepare_out_svl_vals(quantity, company)

    def _convert_origin_svls(self, quantity, company, svls):
        svls_list = []
        for s in svls:
            is_return_available, return_message = s.check_return_available()
            if is_return_available in [False]:
                raise ValidationError(return_message)
            move_svls = s.l10n_ro_svl_track_dest_ids.mapped(
                "svl_dest_id.l10n_ro_svl_return_ids"
            ).filtered(lambda x: not x.l10n_ro_svl_track_dest_ids)
            if s.remaining_qty > 0:
                move_svls |= s
            for ms in move_svls:
                qty = min(quantity, ms.quantity - s.l10n_ro_qty_returned)
                if qty <= 0:
                    continue
                # Valoarea unitara reala (dupa LC)
                unit_value_origin = (
                    ms.value + sum(ms.mapped("stock_valuation_layer_ids.value"))
                ) / (ms.quantity + sum(ms.mapped("stock_valuation_layer_ids.value")))
                value_origin = unit_value_origin * qty
                track_svl = [(ms.id, qty, value_origin, s.id)]
                vals = {
                    "value": -value_origin,
                    "unit_cost": value_origin,
                    "quantity": -qty,
                }
                vals.update({"l10n_ro_tracking": track_svl})
                svls_list.append(vals)
                if ms.remaining_qty > 0:
                    ms.write(
                        {
                            "remaining_qty": ms.remaining_qty - qty,
                            "remaining_value": ms.remaining_value - value_origin,
                        }
                    )
                quantity -= qty
        return svls_list

    def _l10n_ro_prepare_out_svls_vals_return(self, quantity, company, origin_svl_ids):
        vals_tpl = {
            "product_id": self.id,
            "value": 0,
            "unit_cost": self.standard_price,
            "quantity": quantity,
        }
        origin_svls = self.env["stock.valuation.layer"].browse(origin_svl_ids)
        svls_vals_list = self._convert_origin_svls(abs(quantity), company, origin_svls)
        for svls_vals in svls_vals_list:
            vals = vals_tpl.copy()
            vals["quantity"] = svls_vals.get("quantity", 0)
            vals["value"] = svls_vals.get("value", 0)
            vals["remaining_qty"] = svls_vals.get("remaining_qty", 0)
            vals["l10n_ro_tracking"] = svls_vals.get("l10n_ro_tracking")
        return svls_vals_list
