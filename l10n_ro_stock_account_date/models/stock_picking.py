# Copyright (C) 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "l10n.ro.mixin"]

    l10n_ro_accounting_date = fields.Datetime(
        "Accounting Date",
        copy=False,
        help="If this field is set, the svl and accounting entiries will "
        "have this date, If not will have the today date as it should be",
        tracking=True,
    )

    def _action_done(self):
        """Update date_done from accounting_date field"""
        res = super()._action_done()
        for picking in self.filtered("is_l10n_ro_record"):
            if picking.l10n_ro_accounting_date:
                if picking.l10n_ro_accounting_date.date() > fields.date.today():
                    raise ValidationError(
                        _(
                            "You can not have a Accounting date=%s for picking "
                            "bigger than today!"
                            % picking.l10n_ro_accounting_date.date()
                        )
                    )
                picking.write(
                    {
                        "date_done": picking.l10n_ro_accounting_date,
                    }
                )
        return res
