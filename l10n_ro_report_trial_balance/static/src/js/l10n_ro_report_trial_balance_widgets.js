odoo.define('l10n_ro_report_trial_balance.l10n_ro_report_trial_balance_widget', function
(require) {
'use strict';

var core = require('web.core');
var Widget = require('web.Widget');


var AccountReportWidget = Widget.extend({
    events: {
        'click .o_l10n_ro_report_trial_balance_web_action': 'boundLink',
        'click .o_l10n_ro_report_trial_balance_web_action_multi': 'boundLinkmulti',
    },
    init: function(parent) {
        this._super.apply(this, arguments);
    },
    start: function() {
        return this._super.apply(this, arguments);
    },
    boundLink: function(e) {
        var res_model = $(e.target).data('res-model');
        var res_id = $(e.target).data('active-id');
        return this.do_action({
            type: 'ir.actions.act_window',
            res_model: res_model,
            res_id: res_id,
            views: [[false, 'form']],
            target: 'current'
        });
    },
    boundLinkmulti: function(e) {
        var res_model = $(e.target).data('res-model');
        var domain = $(e.target).data('domain');
        return this.do_action({
            type: 'ir.actions.act_window',
            res_model: res_model,
            domain: domain,
            views: [[false, "list"], [false, "form"]],
            target: 'current'
        });
    },
});

return AccountReportWidget;

});
