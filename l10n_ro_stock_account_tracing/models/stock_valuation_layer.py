from odoo import api, fields, models


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    l10n_ro_picking_id = fields.Many2one(
        "stock.picking",
        related="stock_move_id.picking_id",
        string="Stock Picking",
        store=True,
    )
    l10n_ro_picking_type_id = fields.Many2one(
        "stock.picking.type",
        related="l10n_ro_picking_id.picking_type_id",
        store=True,
        string="Picking Type",
    )
    l10n_ro_direction = fields.Selection(
        [("in", "Input"), ("out", "Output")],
        compute="_compute_direction",
        store=True,
        string="Romania Direction",
    )
    l10n_ro_abs_value = fields.Float(
        compute="_compute_direction", store=True, string="Romania Absolute Value"
    )

    @api.depends("value")
    def _compute_direction(self):
        for s in self:
            s.l10n_ro_direction = s.value >= 0 and "in" or "out"
            s.l10n_ro_abs_value = abs(s.value)

    def _setOnAMLInv(self, aml):
        picking_id = (
            location_id
        ) = location_dest_id = valued_type = picking_type_id = None
        if self.stock_move_id:
            (
                picking_id,
                location_id,
                location_dest_id,
                valued_type,
                picking_type_id,
            ) = aml._getAmlData(self.stock_move_id)
        # aml.picking_id = picking_id and picking_id.id
        aml.l10n_ro_location_id = location_id and location_id.id
        aml.l10n_ro_location_dest_id = location_dest_id and location_dest_id.id
        aml.l10n_ro_valued_type = valued_type
        aml.l10n_ro_picking_type_id = picking_type_id and picking_type_id.id
        aml.l10n_ro_link_stock_move_ids = [
            (4, stock.id) for stock in self.mapped("stock_move_id")
        ]

    def _setOnAMLSyntetic(self, aml):
        syntetic_field = aml.debit > 0 and "credit" or "debit"
        syntetic_account = self.mapped("invoice_line_id.move_id.line_ids").filtered(
            lambda x: getattr(x, syntetic_field) > 0
        )
        if len(syntetic_account) > 0:
            max_amount_aml = max(
                syntetic_account, key=lambda x: getattr(x, syntetic_field)
            )
            self._setOnAMLInv(max_amount_aml)
            aml.move_id.l10n_ro_link_stock_picking_ids = [
                (4, pick.id) for pick in self.mapped("stock_move_id.picking_id")
            ]

    def write(self, values):
        res = super(StockValuationLayer, self).write(values)
        if values.get("invoice_line_id", None):
            inv_line = self.mapped("invoice_line_id")
            if inv_line:
                self._setOnAMLInv(inv_line)
                self._setOnAMLSyntetic(inv_line)
        return res
