odoo.define("l10n_ro_stock_report.StockCardView", function (require) {
    "use strict";

    var StockCardController = require("l10n_ro_stock_report.StockCardController");
    var ListView = require("web.ListView");
    var viewRegistry = require("web.view_registry");

    var StockCardView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: StockCardController,
        }),
    });

    viewRegistry.add("stock_card_button", StockCardView);
});
