import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


MODULES_TO_REMOVE = [
    "l10n_ro_stock_account_notice",
]


def _uninstall_modules(env):
    to_uninstall_modules = env["ir.module.module"].search(
        [("name", "in", MODULES_TO_REMOVE), ("state", "!=", "uninstalled")]
    )
    env.cr.execute(
        "update ir_module_module set state = 'installed' where name in %s",
        (tuple(MODULES_TO_REMOVE),),
    )
    for module in to_uninstall_modules:
        _logger.info(f"Found module: {module.name} with current state {module.state}")
        if module.state in ("installed", "to upgrade"):
            _logger.info(f"Uninstalling module: {module.name}")
            module.button_uninstall()
            _logger.info(f"Module {module.name} uninstalled successfully")
        else:
            _logger.info(
                f"Module {module.name} is already uninstalled or "
                f"in an unexpected state: {module.state}"
            )


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _uninstall_modules(env)
