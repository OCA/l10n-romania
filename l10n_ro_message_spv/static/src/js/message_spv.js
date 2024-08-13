odoo.define("account.message.spv.tree", function (require) {
    "use strict";
    console.log(
        "Hello from nexterp_dev/14.0/nexterp/l10n-romania/l10n_ro_message_spv/static/src/js/message_spv.js"
    );

    var ListController = require("web.ListController");
    var ListView = require("web.ListView");
    var viewRegistry = require("web.view_registry");

    const MessageSPVListController = ListController.extend({
        buttons_template: "MessageSPV.buttons",
        events: _.extend({}, ListController.prototype.events, {
            "click .o_button_refresh": "_onClickRefresh",
        }),
        _onClickRefresh: function () {
            this.do_action(
                "l10n_ro_message_spv.ir_cron_res_company_download_message_spv_ir_actions_server",
                {}
            );
        },
    });

    var MessageSPVListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: MessageSPVListController,
        }),
    });

    viewRegistry.add("message_spv_tree", MessageSPVListView);
});
