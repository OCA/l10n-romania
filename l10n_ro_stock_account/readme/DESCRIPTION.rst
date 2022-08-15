With this modue for Romanian companies:

If a product is sorable and has valuation_type automatic, based on source and destination of the stock_move, 
    (receptions, deliveries, consume, usage_giving, inventory and  production) we are going to create
    accounting entries and stock_valuation

For a product that has valuation_type manual we do not create any svl or accounting entries because is suposed 
from time to time to make the inventory and put in accounting a entry based on it

For consumable products we are not going to make stock_valuation_entries at moves because when they enter, 
    is creded a consumed journal entry no stock_account is modified,
    and vhen we use/sell them we just make income, 


!!! In this module, is suposed that the value of purchase product is the same also in invoice 
    ( the modification of svl based on invoice is not in in another module)
    If is a diffrence of values between purchase_order value and invoice_value, in 3xx will be the right value
    and the diffrence will be default_cash_difference_income_account_id  or 999002 Cash Difference Gain with debit or credit
    If the invoice qty is less than what is to invoice will compute for that qty and adding cash difference
    If the inoivced qty is bigger is jut creating the entry wihtout any difference

In Romania, when the sockable product gets into deposit is increasing the stock_value ( and account 3xx), at invoice we are setting the right value of stock and 3xx 
    when the product is getting out of stock is crating expense 6xx and is decresing the stock_value ( and account 3xx) at sale invoice we are making revenue 7xx
     
At reception, the price put into svl is taken from purchase order, 


On companies that have partner_id.country= romania is setting 
"l10n_ro_accounting": True,
"anglo_saxon_accounting": True,        # the check is anglo_saxon_accounting, but romanian accounting is a mix     
"l10n_ro_stock_acc_price_diff": True,

In location we have 
l10n_ro_property_account_income_location_id
l10n_ro_property_account_expense_location_id
l10n_ro_property_stock_valuation_account_id
 and if set will overwrite the accounts set on product if it has l10n_ro_stock_account_change
 
 Contraint on product to have stock_input = stock_output = stock_val
 
 Account_move_line
 method _l10n_ro_get_valuation_stock_moves, if move is from self.purchase_line_id or self.sale_line_ids
 retuns stock_moves that are should be valuated. for  self.move_id.move_type in ("in_refund", "out_invoice", "out_receipt"):
 retuns stock_moves that are considered out sm._is_out()
  else that are considered out sm._is_in()
    !!!! If the account_move is entry, will retun only in
    
At posting of a invoice that is from puchse/sale will set the l10n_ro_invoice_line_id and l10n_ro_invoice 
    on coreponding stock_moves.stock_valuation_layer_ids 

In stock_valuation_layer we are adding
    l10n_ro_valued_type = fields.Char()  reception ...
    l10n_ro_invoice_line_id -> account.move.id
    l10n_ro_invoice_id -> account.move
    l10n_ro_account_id -> account.account compute based on product and location form move

in stock_move_line
    mthod _create_correction_svl    
    
in stock_move
    
At purchase return will show atention if in svl does not exist retuned qty. In this case will take what is in stock at whatever svl value.
The problem can be be at the value of 3xx at Vendor Credit Note 
     