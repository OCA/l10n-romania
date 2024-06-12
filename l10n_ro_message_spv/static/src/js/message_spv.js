odoo.define("account.message.spv.tree", function (require) {
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
            self.do_action(
                "l10n_ro_message_spv.ir_cron_res_company_download_message_spv_ir_actions_server",
                {}
            );
        });
        this.$buttons.append(refresh_button);
        if ($node) {
            this.$buttons.appendTo($node);
        }
    }

    var MessageSPVListController = ListController.extend({
        renderButtons: function () {
            this._super.apply(this, arguments);
            return messageRenderButtons.apply(this, arguments);
        },
    });

    var MessageSPVListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: MessageSPVListController,
        }),
    });

    viewRegistry.add("message_spv_tree", MessageSPVListView);
});
