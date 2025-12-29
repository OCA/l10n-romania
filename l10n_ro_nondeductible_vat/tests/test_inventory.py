# Copyright (C) 2021 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import logging

from odoo.tests import tagged

from .common import TestNondeductibleCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestNonDeductibleInvoice(TestNondeductibleCommon):
    @TestNondeductibleCommon.setup_country("ro")
    def setUp(cls):
        super().setUp()

    # Test minus inventar nedeductibil
