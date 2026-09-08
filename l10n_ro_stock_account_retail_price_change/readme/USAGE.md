## Changing a shelf price

The shop can start from either end.

**From the document.** *Inventory → Retail → Price Changes*, create one,
pick the warehouse, *Load Products*. Every product on hand in the shop's
retail locations comes in with what it currently carries on the left —
cost, markup and deferred VAT per unit, read from the markup ledger, not
from the price list — and the current shelf price on the right. Edit the
*New PVA* of the lines that are changing, delete the rest, then *Post*.

**From the price list.** Change the price of a product on a shop's
retail pricelist, and a draft Proces Verbal is raised for each retail
warehouse that has that product on hand. It is a draft on purpose:
somebody reviews it and posts it. Deleting a rule raises one too, because
the label changes then as well.

Posting does four things, in one transaction: writes the new prices on
the retail pricelist, posts the revaluation of 371 against 378 and 4428,
records it in the markup ledger so the next sale releases the new markup,
and prints as the *Proces-verbal privind modificarea pretului de vanzare
cu amanuntul*.

The old side and the quantity are re-read at the moment of posting, not
at the moment of loading. A draft raised this morning and posted this
afternoon measures itself against what the shop holds this afternoon, so
two documents on the same goods cannot each revalue from the same
starting point.

## Correcting a document

There is no reset to draft, and a posted document cannot be cancelled or
deleted. It wrote prices, posted an entry and moved what the stock
carries; the paper trail is the point. A price decision that turned out
wrong is revoked the way it was made — post another Proces Verbal
bringing the price back. Only a document still in draft can be cancelled
or deleted.

## Price history

*Price History* on a product lists every posted line that concerns it,
oldest first: the date, the shop, the old and new PVA and the document
that decided each. That is the shelf price history the shop has to be
able to show.

## What does not raise a document

Only fixed prices set per product or per template are followed. Category
rules, global rules and formula rules are defaults over a whole range,
and turning one of them into a revaluation of everything underneath is
almost never what the shop means — raise the document by hand.

A **dated** promotion is a real limitation to know about. Editing the
window of a rule is caught, because it is a write. The day a future
window opens is not: nothing is written then, the price list simply
starts answering with another price, and 371 stays on the old PVA until
somebody raises the document. Plan dated shelf prices with a Proces
Verbal on the day they take effect.
