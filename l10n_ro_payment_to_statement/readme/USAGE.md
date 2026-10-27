## Registering a payment

Post a payment in a cash journal which keeps a register, from the payment
itself or from the *Register Payment* button of an invoice. The payment
takes its number from the sequence of its kind, and the register of the day
gets a line for it, reconciled with the payment.

The line is already reconciled, so it does not show up in the bank
reconciliation screen, and the balance of the register follows the payments
of the day.

Cancelling a payment, or setting it back to draft, takes its register line
away with it; posting it again makes a new one. A payment posted again with
the same amount on another day moves to the register of that day, unless it
is alone in its own register, which then simply follows it.

## Cash in and cash out slips

A line made straight in the register, without a payment behind it, joins
the register of its day too.

## The balance of the register

The module computes the balance of the register from its lines. The
*Ending Balance* is left to whoever counts the money: the module never
writes it.
