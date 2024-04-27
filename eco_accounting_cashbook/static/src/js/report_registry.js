odoo.define('eco_accounting_cashbook.action_report_cashbook', function (require) {
    "use strict";
    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');
    var datepicker = require("web.datepicker");
    const { ComponentWrapper } = require('web.OwlCompatibility');
    const {CashBook} = require("@eco_accounting_cashbook/js/report_cash_book")
    var _t = core._t;
  
    var QWeb = core.qweb;
  
  
    var Dashboard = AbstractAction.extend({
      hasControlPanel: false,
      init(parent, action, options={}) {
        this._super(...arguments);
        this.component = undefined;
        this.action = action;
        this.props = {
            ui: action.ui,
            data: action.data,
            action: action,
            doAction: this.do_action
        };
    },
    async start() {
        await this._super(...arguments);
        this.$el.find('.o_cp_bottom').hide();
        this.component = new ComponentWrapper(this, CashBook, this.props);
        return this.component.mount(this.el.querySelector('.o_content'));
    }
    })
  
    core.action_registry.add('action_report_cashbook', Dashboard);
    return Dashboard;
  })