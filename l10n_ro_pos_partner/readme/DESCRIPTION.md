A company buying over the counter identifies itself by its CUI, and that code
is rarely on file before the first sale. Searching for it in the *Choose
customer* dialog of the Point of Sale would normally end on "no customers
found" -- yet the company is public record at ANAF.

This module turns that dead end into the way company customers are added at
the till:

- a search that reads as a Romanian CUI is recognised as one, with or without
  the `RO` prefix, since the customer reading it off a document does not know
  which of the two the shop keeps;
- a customer already on file under that CUI is offered straight away, even
  when the cashier would never have found them by name;
- when there is none, a **Create from ANAF** button fetches the company --
  name, VAT status, registration number and registered address -- creates it
  and puts it on the order in one step. The same ANAF history the partner form
  keeps is recorded, so it does not matter that the customer came in through
  the till.

Choosing a company as the customer does not turn the receipt into an invoice.
In Romania the fiscal receipt is what the till issues and it settles the sale
on its own; the invoice is asked for, not assumed.
