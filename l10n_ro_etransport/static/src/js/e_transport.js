odoo.define("e.transport.history.tree", function (require) {
    "use strict";

    var ListController = require("web.ListController");
    var ListView = require("web.ListView");
    var viewRegistry = require("web.view_registry");

    function messageRenderButtons($node) {
        var self = this;
        var refresh_button = $("<div/>");
        refresh_button.html(
            '<button class="btn btn-secondary"><i class="fa fa-refresh"/></button>'
        );
        refresh_button.find("button").on("click", function () {
            self.do_action("l10n_ro_etransport.action_e_transport_refresh", {});
        });
        this.$buttons.append(refresh_button);
        if ($node) {
            this.$buttons.appendTo($node);
        }
    }

    var ETransportHistoryListController = ListController.extend({
        renderButtons: function () {
            this._super.apply(this, arguments);
            return messageRenderButtons.apply(this, arguments);
        },
    });

    var ETransportHistoryListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: ETransportHistoryListController,
        }),
    });

    viewRegistry.add("e_transport_history_tree", ETransportHistoryListView);
});
