/** @odoo-module **/
// const { onMounted, onWillStart, useRef, useSubEnv, useState } = owl.hooks;
const { loadAssets } = require("@web/core/assets");
const { ComponentWrapper } = require('web.OwlCompatibility');
import { DatePicker } from '@web/core/datepicker/datepicker';
import InputAutoComplete from 'eco_accounting_cashbook.InputAutoComplete'
import session from 'web.session';
const { DateTime } = luxon;
import { useService } from "@web/core/utils/hooks";

var { Component, onMounted, xml } = require("@odoo/owl");

const { useState, onPatched, onWillUnmount, useRef } = owl;

export class CashBook extends Component {

  constructor(parent, props) {
    super(...arguments);

    const today = new Date();
    const from = new Date(today.getFullYear(), today.getMonth(), 1);
    const to = new Date(today.getFullYear(), today.getMonth() + 1, 0);

    this.state = useState({
      scale: 1,
      pan: {
        x: 0,
        y: 0,
      },
      count: 5,
      nodes: [],
      connections: [],
      from_date: DateTime.fromJSDate(from),
      end_date: DateTime.fromJSDate(to),
      account_id: null,
      move_ids: [],
      out_debit: 0,
      company: '',
      code: 0,
    })

    this.input_ref = useRef('input_ref');
    // this.notification = useService("notification");
  }

  toStrDate(date) {
    return date.toFormat('dd-MM-yyyy')
  }

  _onChangeAccount(data) {
    this.state.account_id = data.account_id;
    var self = this;
    this.env.services.rpc({
      route: '/eco_accounting_cashbook/objects/account_company',
      params: {
        account_id: data.account_id,
      },
    }).then(response => {
      self.state.company = response.company;
      self.state.code = response.code;
    })
  }

  action_view_report() {
    if (!this.validate()) {
      return
    }
    var self = this;
    this.env.services.rpc({
      route: '/eco_accounting_cashbook/objects/action_report',
      params: {
        account_id: self.state.account_id,
        from_date: self.state.from_date.toFormat('yyyy-MM-dd'),
        to_date: self.state.end_date.toFormat('yyyy-MM-dd'),
      },
    }).then(response => {
      self.state.move_ids = response.move_lines
      self.state.out_debit = response.out_debit
    });
  }

  action_export_report() {
    if (!this.validate()) {
      return
    }
    var self = this;
    this.env.services.rpc({
      route: '/eco_accounting_cashbook/objects/export_excel',
      params: {
        account_id: self.state.account_id,
        from_date: self.state.from_date.toFormat('yyyy-MM-dd'),
        to_date: self.state.end_date.toFormat('yyyy-MM-dd'),
      },
    }).then(response => {
      self.props.doAction(response)
    });
  }

  onDateStartChanged(date) {
    this.state.from_date = date
    console.log(date.toFormat('yyyy-MM-dd'));
  }

  onDateEndChanged(date) {
    // console.log(data);
    this.state.end_date = date;
    console.log(date.toFormat('yyyy-MM-dd'));
  }

  _onChangeInput(ev) {
    console.log(ev.target.value);
  }

  formatCurrency(amount) {
    return amount.toLocaleString('vi-VN')
  }

  validate() {
    if (!this.state.account_id) {
      this.env.services.notification.notify({
        title: "Lỗi",
        message: this.env._t(
          "Giá trị đầu tài khoản là bắt buộc!"
        ),
        type: "danger",
      });
      return false
    }
    if (this.state.from_date > this.state.from_date) {
      this.env.services.notification.notify({
        title: "Lỗi",
        message: this.env._t(
          "Ngày bắt đầu không được lớn hơn ngày kết thúc!"
        ),
        type: "danger",
      });
      return false
    }
    return true
  }

}

CashBook.template = 'CashBook';
CashBook.components = { DatePicker, InputAutoComplete }