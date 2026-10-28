In Romania a fiscal receipt cannot be reversed by printing a negative one:
the refund has to go out as a credit note ("factura storno"), and the cash
given back over the counter has to be covered by a payment disposal
("dispozitie de plata") the customer signs for.

This module makes both of them happen on their own. Refunding a receipt in
the Point of Sale creates a regular refund order, and as soon as it is paid:

- the credit note is issued on the invoice journal of the Point of Sale --
  invoicing a refund is not optional any more. The cashier is asked for the
  customer as soon as the refund is created, and the payment screen says why
  it cannot be validated without one;
- the cash returned is registered as its own cash statement line, linked to
  the session and settling the credit note directly. That line is the payment
  disposal, and it comes out of the printer at the till right behind the
  credit note, for the customer to sign.

A refund either produces a real credit note or does not happen at all. Where
core would attach a proforma and carry on -- an e-Factura that will not build
over a partner missing its county, say -- the refund is refused instead, with
the reason, because a proforma reverses nothing. An e-Factura that builds but
cannot reach the SPV is a different matter: the credit note is real, the
refund goes through, and the upload is retried from the back office.

The cash leaves the till once: the POS payment behind a payment disposal is
kept out of the session's cash flow and out of its closing entry, because the
statement line already carries it.
