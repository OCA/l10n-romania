Functionalitati

Daca este instalat modulul l10n\_ro\_stock\_account se genereaza note
contabile la fiecare miscare iesire stoc. Acest modul nu mai genereaza
in nota contabla de inchiderea a sesiunii POS liniile aferente iesirii
din gestiune.

Afisare mesaje de avertizare pentru vanzare cu numerar mai mare de 5000.

## One registru de casa per shop

Core lets a cash journal serve a single payment method, so every register
ends up with a cash journal of its own. A Romanian shop running several
registers in the same place keeps one *registru de casa* for that place --
the cash of all of them is a single till, counted and reported together --
so their payment methods point at the same cash journal.

Each register still needs a payment method of its own: it closes its own
drawer, and a method shared between two registers would mix them.

## Invoicing a receipt on request

The fiscal receipt settles the sale on its own, so nothing is invoiced by
default. A customer who needs an invoice asks for one at the counter, and the
receipt screen has a **Generate Invoice** button for exactly that moment: it
invoices the order that was just paid and hands the PDF over. The button only
shows once the order has reached the server, has a customer, and is not
invoiced already.
