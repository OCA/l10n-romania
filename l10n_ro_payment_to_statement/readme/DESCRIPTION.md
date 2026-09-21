Keeps the cash register (registru de casa) of a cash journal.

Every payment posted in a cash journal set to keep a register is added to
the register of its day, which is opened when it does not exist yet. The
line of the register never has to be reconciled: it stands for a payment
which is already reconciled with its invoice.

The module also numbers the documents of a cash journal with sequences of
its own, instead of letting Odoo build the numbers: receipt (chitanta),
cash in and cash out slips (dispozitie de incasare / de plata) and the
register itself.

A sequence can be set on any other journal as well, in *Journal sequence*,
and the entries of that journal are then numbered from it: the invoices of
a sale journal, the bills of a purchase one, the entries of a
miscellaneous one.
