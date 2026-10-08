# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, api, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _l10n_ro_retail_warehouse(self):
        """The shop this point of sale sells from, when it is kept at retail.

        A till is attached to a warehouse through its operation type. Only a
        warehouse marked as retail is of interest here: that is the one whose
        goods sit on 371 at the price on the label, and whose markup and
        deferred VAT the sale has to unwind.
        """
        self.ensure_one()
        warehouse = self.picking_type_id.warehouse_id or self.warehouse_id
        return warehouse if warehouse.l10n_ro_retail else warehouse.browse()

    def _l10n_ro_retail_shop_values(self):
        """What a till takes over from the shop it sells from.

        The fiscal position, because it is what carries both halves of the
        shop's setup: the taxes the shelf price is split with, and the
        accounts the goods, the markup and the deferred VAT are kept on. And
        the retail price list, because the price the cashier charges has to
        be the price on the label.

        Only empty fields are filled. A shop that deliberately runs a till on
        another price list - a staff canteen, a clearance corner - keeps it.
        """
        self.ensure_one()
        warehouse = self._l10n_ro_retail_warehouse()
        if not warehouse:
            return {}
        values = {}
        fiscal_position = warehouse.l10n_ro_fiscal_position_id
        if fiscal_position and not self.default_fiscal_position_id:
            values["default_fiscal_position_id"] = fiscal_position.id
            values["fiscal_position_ids"] = [Command.link(fiscal_position.id)]
        pricelist = warehouse.l10n_ro_retail_pricelist_id
        if pricelist and not self.pricelist_id:
            values["pricelist_id"] = pricelist.id
            # The core constraint refuses a default price list that is not
            # among the available ones, so it goes in both.
            values["available_pricelist_ids"] = [Command.link(pricelist.id)]
        return values

    def _l10n_ro_apply_retail_shop(self):
        """Fill in what the shop decides, on tills that do not say otherwise.

        Called when a till is created and when the bridge is installed, so a
        database that already had its shops and its tills gets them to agree
        without going through every point of sale by hand.
        """
        for config in self:
            values = config._l10n_ro_retail_shop_values()
            if values:
                config.write(values)

    @api.model_create_multi
    def create(self, vals_list):
        configs = super().create(vals_list)
        configs._l10n_ro_apply_retail_shop()
        return configs

    @api.onchange("picking_type_id")
    def _onchange_l10n_ro_retail_shop(self):
        """Propose the shop's setup as soon as the till is pointed at it."""
        for field_name, value in self._l10n_ro_retail_shop_values().items():
            self[field_name] = value
