/** @odoo-module **/

import {ListController} from "@web/views/list/list_controller";
import {listView} from "@web/views/list/list_view";
import {registry} from "@web/core/registry";

export class MessageSPVListController extends ListController {
    async onRefreshClick() {
        await this.env.services.orm.call("res.company", "l10n_ro_download_message_spv");
        await this.model.load();
    }
}

registry.category("views").add("message_spv_tree", {
    ...listView,
    Controller: MessageSPVListController,
    buttonTemplate: "MessageSPV.buttons",
});
