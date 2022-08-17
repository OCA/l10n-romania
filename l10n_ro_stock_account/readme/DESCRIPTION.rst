With this modue for Romanian companies:

If a product is sorable and has valuation_type automatic, based on source and destination of the stock_move, 
    (receptions, deliveries, consume, usage_giving, inventory and  production) we are going to create
    accounting entries and stock_valuation

For a product that has valuation_type manual we do not create any svl or accounting entries because is suposed 
from time to time to make the inventory and put in accounting a entry based on it

For consumable products we are not going to make stock_valuation_entries at moves because when they enter, 
    is creded a consumed journal entry no stock_account is modified,
    and vhen we use/sell them we just make income, 


In Romania, the products get into stock with supplier invoice/bill ( and svl is created based on the values from bill).
Another case is when the products are geting into stock with a value (picking type notice) and after a time is coming the bill - is covered in l10n_ro_stock_notice module

To make the svl and accouting entries for stock account, the procurments and deliveries must be done from pucase/sales.



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
 
    
In stock_valuation_layer we are adding
    l10n_ro_valued_type   # just a name we can live also without
    l10n_ro_bill_accounting_date  This is the date from billing accounting date. The bill that generate this svl
    l10n_ro_draft_history  text each time, the bill that generated this was set to draft 

in stock_move_line
    mthod _create_correction_svl    
    
in stock_move

     