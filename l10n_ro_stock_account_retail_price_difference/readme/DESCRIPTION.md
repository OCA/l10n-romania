# Romania - Retail Price Difference (Marfa in Magazin)

A vendor bill that comes in above the reception price raises the cost of
goods that may already be on a shelf. In this localization such a price
difference is a landed cost, so
`l10n_ro_stock_account_retail_landed_cost` already keeps 371 at the
shelf price and moves the difference out of the markup.

What this module adds is the answer before the fact. The confirmation
dialog that lists the price differences now also shows, per line, the
markup the goods carry today, what the difference leaves of it, and
whether the shelf price still covers the cost - so the decision to post
the bill is taken knowing whether a Proces Verbal de Schimbare Pret is
needed first, instead of finding out when the posting is refused.

Installs itself as soon as both retail landed cost and price difference
are present.
