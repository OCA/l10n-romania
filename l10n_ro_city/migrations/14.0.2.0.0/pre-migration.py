# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE ir_model_data SET module = 'l10n_ro_city'
        WHERE model = 'res.city' and name like '%RO_%';;
        """
    )
