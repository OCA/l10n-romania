# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Bring the tills of the existing shops in line on installation.

    The bridge is auto installed, so it usually arrives on a database that
    already has both its shops and its points of sale. Waiting for someone to
    open each one and save it would leave those tills selling on the ordinary
    taxes and accounts in the meantime.
    """
    configs = env["pos.config"].search([])
    configs = configs.filtered(lambda config: config._l10n_ro_retail_warehouse())
    if configs:
        _logger.info(
            "Applying the retail shop setup on %s points of sale", len(configs)
        )
        configs._l10n_ro_apply_retail_shop()
