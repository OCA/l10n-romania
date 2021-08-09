description
    in journal type cache you can add cache_in_sequence -
    to generate numbers based on this sequence at cash outgoing account.payment

    in account.payment you have a new filed
    payment_out_number = fields.Char('Cash seq number',default='',help=
    If is a cache out payment will have a number given from the sequence
    from cache journal or next number ( from last date/id)"
    If you are the account manger, you can see this field and
    you can modify it."
    It you modify it, the payment will have this number."
    If no number at the end of sequence (and no cache journal
    in sequence) will start from default C0001",tracking=1)

    and a name computed field to take the value from move_id
    where the payment did not generate payment_out_number
    name = fields.Char(compute="_compute_payment_name",
    computed name as payment_out_number if exist, if not will be the name
    from move_id

    At install will create numbers for cache_account_payments
    ( you can modify them later), but in general if you want to
    use them in accounting is good to have a series
