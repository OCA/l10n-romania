.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

=============================
Romania - Payroll Application
=============================

This module deals with Romanian Payroll implementation.
It adds multiple configuration including:

Wage History
------------
* Used to compute base for Sick Leaves and others as given by `ANAF <http://static.anaf.ro/static/10/Anaf/Declaratii_R/AplicatiiDec/structura_dunica_A304_2015_230115.pdf>`_

Meal Vouchers
-------------
* Set the value of the meal voucher in Company -> HR
* Calculates the number of vouchers per employee
* Meal voucher report

Salary Categories and Rules
---------------------------
* As default it adds a single Salary Structure to include basic calculation of salaries in Romania.

Employee Income History
-----------------------
* You have a history about employee incomes, calculated directly from Payroll, or inputed for previous months.

Installation
============

To install this module, you need to:

* clone the branch 11.0 of the repository https://github.com/OCA/l10n-romania
* add the path to this repository in your configuration (addons-path)
* update the module list
* search for "Romania - Payroll" in your addons
* install the module

Usage
=====



.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/177/11.0

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/l10n-romania/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smash it by providing detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Fekete Mihai <feketemihai@gmail.com>
* Dorin Hongu <dhongu@gmail.com>
* Adrian Vasile <adrian.vasile@gmail.com>

Do not contact contributors directly about support or help with technical issues.

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
