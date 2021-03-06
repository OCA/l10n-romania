odoo.define("l10n_ro_stock_report.StockCardController", function (require) {
    "use strict";

    var core = require("web.core");
    var ListController = require("web.ListController");

    var qweb = core.qweb;

    var StockCardController = ListController.extend({
        events: _.extend(
            {
                "click .o_button_print_stock_card": "_onPrintStockCard",
            },
            ListController.prototype.events
        ),

        init: function (parent, model, renderer) {
            var context = renderer.state.getContext();
            this.stock_card_id = context.active_id;
            return this._super.apply(this, arguments);
        },

        renderButtons: function () {
            this._super.apply(this, arguments);
            this.$buttons.find(".o_button_import").addClass("d-none");
            var $validationButton = $(qweb.render("StockCardReport.Buttons"));
            this.$buttons.prepend($validationButton);
        },

        // -------------------------------------------------------------------------
        // Handlers
        // -------------------------------------------------------------------------

        _onPrintStockCard: function (ev) {
            ev.stopPropagation();
            var self = this;

            return self.do_action("l10n_ro_stock_report.action_report_stock_card_all", {
                additional_context: {
                    active_id: self.stock_card_id,
                    active_ids: [self.stock_card_id],
                    active_model: "stock.daily.stock.report",
                },
            });
        },
    });

    return StockCardController;
});
