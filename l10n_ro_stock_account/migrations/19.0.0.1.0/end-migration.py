import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


MODULES_TO_REMOVE = [
    "l10n_ro_stock_account_notice",
]


def _uninstall_modules(env):
    _logger.info("Uninstalling l10n_ro_stock_account_notice module")
    env.cr.execute(
        "update ir_module_module set state = 'uninstalled' where name in %s",
        (tuple(MODULES_TO_REMOVE),),
    )


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _uninstall_modules(env)
