Features:

>   - Adding the payments in the bank statements
> 
> This module added features on customer/supplier payments to allow
> account user to link payment with bank statement direct through
> payment menu or customer/supplier invoices register payment option.
> After selecting and validating payment, module will add bank statement
> line on selected bank statement.
> 
>   - Sequences can be attached to journals, so the invoices/payments
>     are not computed by odoo, but taken from the selected sequences:
> 
> >   - Journal sequence: for sale journals, this will be the invoice's
> >     sequence. For cash/bank journals, this will be the sequence for
> >     other journal entries (for closing the statement, for statement
> >     lines etc.)
> >   - Customer sequence cash in: only for cash journals. This sequence
> >     will be used for customer payments
> >   - Statement sequence: only for cash/bank journals. This sequence
> >     will be used for bank/cash statements
> >   - Cash in sequence: only for cash. This sequence will be used for
> >     supplier refunds
> >   - Cash out sequence: only for cash. This sequence will be used for
> >     customer refunds
