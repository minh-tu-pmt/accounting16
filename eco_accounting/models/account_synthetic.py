from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import AccessError, ValidationError


class AccountSynthetic(models.Model):
    _name = 'account.synthetic'
    _order = 'id desc'
    _rec_name = 'partner_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    partner_id = fields.Many2one('res.partner', 'Khách hàng')
    partner_bank_id = fields.Many2one('res.partner.bank',string="TKNH đối tác")
    payment_type_detail = fields.Selection([('follow_detail_invoice', 'Follow Details Invoice'), ('follow_partner', 'Follow Partner')], string="Loại thanh toán", default='follow_partner', required=True)
    detail_account_vat_gtgt_ids = fields.One2many('vat.gtgt', 'synthetic_id', string="Tab thuế đầu ra đầu vào")
    detail_account_expenditure_ids = fields.One2many('detail.acccount.payment.expenditure','synthetic_id',string="Ủy nghiệm chi")
    act_advanced_id = fields.Many2one('act.advance',string='Tạm ứng')
    type_journal = fields.Selection([('cash','Cash'),('bank','Bank')])

    name = fields.Char('Số chứng từ', readonly=True, default=lambda self: 'New', copy=False)

    @api.model
    def create(self, vals_list):
        seq = self.env['ir.sequence'].next_by_code('synthetic.sequence') or 'New'
        journal = self.env['account.journal'].search([('id', '=', int(vals_list['journal_id']))])
        vals_list['name'] = f"{journal.code}/{datetime.today().year}/{datetime.today().month}/{seq}"
        result = super(AccountSynthetic, self).create(vals_list)
        return result

    detail_account_payment_invoice_ids = fields.One2many('detail.acccount.payment.invoice', 'payment_synthetic_id', string="Chi tiết")
    detail_account_payment_partner_ids = fields.One2many('detail.acccount.payment.partner', 'payment_synthetic_id', string="Chi tiết")
    journal_id = fields.Many2one('account.journal', store=True, readonly=False,
                                 domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]")
    date = fields.Date('Ngày kế toán', default=fields.Date.today(), required=True)
    move_ids = fields.Many2many('account.move')
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('posted', 'Posted'),
    ], string='Trạng thái', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
    type_pay = fields.Selection([('inbound', 'Receive'), ('outbound', 'Send')], sring="Kiểu thanh toán", default='outbound')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, string="Tiền tệ", required=True)

    amount = fields.Monetary(currency_field='currency_id', compute="_compute_amount_synthetic", inverse='_inverse_amount', store=True, string="Tổng tiền")

    receiver = fields.Char(string='Người nhận tiền')

    person_push = fields.Char('Người nộp tiền')

    form_of_allocation = fields.Selection([('manual', 'Manual'), ('auto', 'Auto')], string="Hình thức phân bổ", default='manual', required=True)
    rate_currency = fields.Float('Tỷ giá', compute='_compute_rate_curr', inverse='_inverse_rate_curr', store=True, digits=(16, 2))
    address = fields.Char(compute='_compute_address', string="Địa chỉ", store=True, inverse='_inverse_address')
    count_paymnet = fields.Integer(compute="_compute_count_payment")
    count_move = fields.Integer(compute="_compute_count_payment")

    check_currency = fields.Boolean(compute="compute_currency", store=True)

    @api.onchange('currency_id')
    def _currency_id_onchange(self):
        for rec in self.detail_account_payment_partner_ids:
            rec.base_value = 0

    def _inverse_amount(self):
        pass

    @api.depends('detail_account_payment_partner_ids.value')
    def _compute_amount_synthetic(self):
        for rec in self:
            if rec.payment_type_detail == 'follow_partner':
                if self.env.company.currency_id.id == rec.currency_id.id:
                    rec.amount = sum([x.value for x in rec.detail_account_payment_partner_ids])
                else:
                    rec.amount = sum([x.base_value for x in rec.detail_account_payment_partner_ids])

    def action_draft(self):
        payment = self.env['account.payment'].search([('synthetic_id', '=', self.id)])
        moves = self.env['account.move'].search([('synthetic_id', '=', self.id)])
        for rec in payment:
            if rec.state != 'draft':
                rec.action_draft()
        if moves:
            for m in moves:
                m.button_draft()
                m.unlink()
        self.state = 'draft'

    @api.onchange('form_of_allocation')
    def form_of_allocation_onchange(self):
        if self.form_of_allocation == 'auto' and self.payment_type_detail == 'follow_detail_invoice':
            for r in self.detail_account_payment_invoice_ids:
                r.chosing = True
                r.value = r.amount_redisual

    @api.depends('currency_id.rate_ids.company_rate', 'currency_id')
    def _compute_rate_curr(self):
        for rec in self:
            if self.env.company.currency_id.id == rec.currency_id.id:
                rec.rate_currency = 1
            elif self.env.company.currency_id.id != rec.currency_id.id and rec.currency_id.rate_ids:
                dicts = [
                    {'rate': x.inverse_company_rate, "date": x.name} for x in rec.currency_id.rate_ids
                ]
                today = datetime.today().date()

                nearest_dict = min(dicts, key=lambda x: abs(x['date'] - today))

                rec.rate_currency = int(nearest_dict['rate'])
            else:
                rec.rate_currency = 1

    def _inverse_rate_curr(self):
        pass

    # @api.onchange('currency_id')
    # def _onchange_currency(self):
    #     for rec in self.detail_account_payment_partner_ids:
    #         rec.base_value = 0
    #         rec.value = 0
    #         rec.amount

    @api.depends('currency_id')
    def compute_currency(self):
        for rec in self:
            if self.env.company.currency_id.id != rec.currency_id.id:
                rec.check_currency = False
            else:
                rec.check_currency = True

    def _compute_count_payment(self):
        for rec in self:
            rec.count_paymnet = len(self.env['account.payment'].search([('synthetic_id', '=', rec.id)]))
            rec.count_move = len(self.env['account.move'].search([('synthetic_id', '=', rec.id)]))

    def action_confirm(self):
        self.state = 'confirm'

    def action_register_payment(self):
        if self.payment_type_detail == 'follow_detail_invoice' and self.form_of_allocation == 'manual':
            if self.amount < sum([x.value if x.chosing else 0 for x in self.detail_account_payment_invoice_ids]):
                raise ValidationError('Số tiền thanh toán vượt quá tổng tiền!')

        if self.payment_type_detail == 'follow_detail_invoice':
            for rec in self.detail_account_payment_invoice_ids:
                if rec.chosing and rec.move_id.currency_id.id != self.currency_id.id:
                    raise ValidationError('Đơn vị tiền tệ của hóa đơn và thanh toán phải cùng một giá trị')

        if self.currency_id.id == self.env.company.currency_id.id:
            if self.payment_type_detail == 'follow_partner':
                if self.type_pay == 'inbound':
                    line_vals_list = {
                        'name': self.description,
                        'date_maturity': self.date,
                        'amount_currency': self.amount,
                        'currency_id': self.currency_id.id,
                        'debit': self.amount,
                        'credit': 0.0,
                        'partner_id': self.partner_id.id if self.partner_id else False,
                        'account_id': self.journal_id.inbound_payment_method_line_ids[0].payment_account_id.id or self.env.company.account_journal_payment_debit_account_id.id,
                        'group_clause': 1,
                    }
                    vals = [(0, 0, line_vals_list)]
                    for rec in self.detail_account_payment_partner_ids:
                        val = {
                            'name': rec.description,
                            'date_maturity': self.date,
                            'amount_currency': rec.base_value,
                            'currency_id': self.currency_id.id,
                            'debit': 0.0,
                            'credit': rec.value,
                            'partner_id': rec.partner_id.id if rec.partner_id else False,
                            'account_id': rec.account_id.id,
                            'group_clause': 1,
                            'indenture_id': rec.indenture_id.id,
                            'item_fee_id': rec.fee_group_id.id
                        }
                        vals.append((0, 0, val))
                else:
                    line_vals_list = {
                        'name': self.description,
                        'date_maturity': self.date,
                        'amount_currency': self.amount,
                        'currency_id': self.currency_id.id,
                        'debit': 0.0,
                        'credit': self.amount,
                        'partner_id': self.partner_id.id if self.partner_id else False,
                        'account_id': self.journal_id.inbound_payment_method_line_ids[0].payment_account_id.id or self.env.company.account_journal_payment_debit_account_id.id,
                        'group_clause': 1,
                    }
                    vals = [(0, 0, line_vals_list)]
                    for rec in self.detail_account_payment_partner_ids:
                        val = {
                            'name': rec.description,
                            'date_maturity': self.date,
                            'amount_currency': rec.base_value,
                            'currency_id': self.currency_id.id,
                            'debit': rec.value,
                            'credit': 0.0,
                            'partner_id': rec.partner_id.id if rec.partner_id else False,
                            'account_id': rec.account_id.id,
                            'group_clause': 1,
                            'indenture_id': rec.indenture_id.id,
                            'item_fee_id': rec.fee_group_id.id
                        }
                        vals.append((0, 0, val))
                move = self.env['account.move'].create({
                    'ref': self.description,
                    'move_type': 'entry',
                    'date': self.date,
                    'journal_id': self.journal_id.id,
                    'currency_id': self.currency_id.id,
                    'line_ids': vals,
                    'synthetic_id': self.id
                })
                move.action_post()
                self.state = 'posted'
                if self.act_advanced_id and self.state == 'posted':
                    self.act_advanced_id.state = 'advanced'
            else:
                if not self.detail_account_payment_invoice_ids.filtered(lambda x: x.chosing):
                    raise ValidationError("Không có hóa đơn nào được chọn!")
                line_vals_list = {
                    'name': self.description,
                    'date_maturity': self.date,
                    'amount_currency': self.amount,
                    'currency_id': self.currency_id.id,
                    'debit': sum([x.value if x.chosing else 0 for x in self.detail_account_payment_invoice_ids]),
                    'credit': 0.0,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'account_id': self.journal_id.default_account_id.id,
                    'group_clause': 1,
                }
                vals = [(0, 0, line_vals_list)]
                for rec in self.detail_account_payment_invoice_ids:
                    if rec.chosing:
                        val = {
                            'name': rec.description,
                            'date_maturity': self.date,
                            'amount_currency': rec.base_value,
                            'currency_id': self.currency_id.id,
                            'debit': 0.0,
                            'credit': rec.value,
                            'partner_id': rec.partner_id.id if rec.partner_id else False,
                            'account_id': rec.account_id.id,
                            'group_clause': 1,
                            'indenture_id': rec.indenture_id.id,
                            'item_fee_id': rec.item_fee_id.id
                        }
                        vals.append((0, 0, val))
                move = self.env['account.move'].create({
                    'ref': self.description,
                    'move_type': 'entry',
                    'date': self.date,
                    'journal_id': self.journal_id.id,
                    'currency_id': self.currency_id.id,
                    'line_ids': vals,
                    'synthetic_id': self.id
                })
                move.action_post()
                ids = []
                for x in self.detail_account_payment_invoice_ids:
                    if x.chosing:
                        ids.append(x.move_id.id)
                self.move_ids = [(6, 0, ids)]
                if self.amount > sum([x.value if x.chosing else 0 for x in self.detail_account_payment_invoice_ids]):
                    return {
                        'name': _('Register Payment'),
                        'res_model': 'account.payment.register',
                        'views': [(self.env.ref('eco_accounting.view_account_payment_register_form_extend').id, 'form')],
                        'view_mode': 'form',
                        'context': {
                            'active_model': 'account.move',
                            'active_ids': self.move_ids.ids,
                            'default_synthetic_id': self.id,
                            'default_journal_id': self.journal_id.id,
                            'default_currency_id': self.currency_id.id,
                            'default_payment_date': self.date,
                            'default_amount': self.amount,
                            'default_group_payment': True
                        },
                        'target': 'new',
                        'type': 'ir.actions.act_window',
                    }
                account_register = self.env['account.payment.register'].with_context(active_model='account.move',active_ids=self.move_ids.ids).create({
                    'synthetic_id': self.id,
                    'journal_id': self.journal_id.id,
                    'currency_id': self.currency_id.id,
                    'payment_date': self.date,
                    'amount': self.amount,
                    'group_payment': True
                })
                account_register.action_create_payments()
        else:
            if self.payment_type_detail == 'follow_partner':
                line_vals_list = {
                    'name': self.description,
                    'date_maturity': self.date,
                    'amount_currency': self.amount,
                    'currency_id': self.currency_id.id,
                    'debit': sum([x.value for x in self.detail_account_payment_partner_ids]),
                    'credit': 0.0,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'account_id': self.journal_id.inbound_payment_method_line_ids[0].payment_account_id.id or self.env.company.account_journal_payment_credit_account_id.id,
                    'group_clause': 1
                }
                vals = [(0, 0, line_vals_list)]
                for rec in self.detail_account_payment_partner_ids:
                    val = {
                        'name': rec.description,
                        'date_maturity': self.date,
                        'amount_currency': -rec.base_value,
                        'currency_id': self.currency_id.id,
                        'debit': 0.0,
                        'credit': rec.value,
                        'partner_id': rec.partner_id.id if rec.partner_id else False,
                        'account_id': rec.account_id.id,
                        'group_clause': 1,
                        'department_id': rec.department_id.id,
                        'analytic_account_id': rec.analytic_account_id.id,
                        'indenture_id': rec.indenture_id.id,
                        'item_fee_id': rec.fee_group_id.id
                    }
                    vals.append((0, 0, val))
                move = self.env['account.move'].create({
                    'ref': self.description,
                    'move_type': 'entry',
                    'rate_curr': self.rate_currency,
                    'date': self.date,
                    'journal_id': self.journal_id.id,
                    'currency_id': self.currency_id.id,
                    'line_ids': vals,
                    'synthetic_id': self.id
                })
                self.state = 'posted'
                if self.act_advanced_id and self.state == 'posted':
                    self.act_advanced_id.state = 'advanced'
            else:
                if not self.detail_account_payment_invoice_ids.filtered(lambda x: x.chosing):
                    raise ValidationError("Không có hóa đơn nào được chọn!")
                line_vals_list = {
                    'name': self.description,
                    'date_maturity': self.date,
                    'amount_currency': sum([x.base_value if x.chosing else 0 for x in self.detail_account_payment_invoice_ids]),
                    'currency_id': self.currency_id.id,
                    'debit': sum([x.value if x.chosing else 0 for x in self.detail_account_payment_invoice_ids]),
                    'credit': 0.0,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'account_id': self.journal_id.default_account_id.id,
                    'group_clause': 1
                }
                vals = [(0, 0, line_vals_list)]
                for rec in self.detail_account_payment_invoice_ids:
                    if rec.chosing:
                        val = {
                            'name': self.description,
                            'date_maturity': self.date,
                            'amount_currency': -rec.base_value,
                            'currency_id': self.currency_id.id,
                            'debit': 0.0,
                            'credit': rec.value,
                            'partner_id': rec.partner_id.id if rec.partner_id else False,
                            'account_id': rec.account_id.id,
                            'group_clause': 1,
                            'indenture_id': rec.indenture_id.id,
                            'item_fee_id': rec.item_fee_id.id
                        }
                        vals.append((0, 0, val))
                move = self.env['account.move'].create({
                    'ref': self.description,
                    'move_type': 'entry',
                    'date': self.date,
                    'rate_curr': self.rate_currency,
                    'journal_id': self.journal_id.id,
                    'currency_id': self.currency_id.id,
                    'line_ids': vals,
                    'synthetic_id': self.id
                })
                move.action_post()
                self.state = 'posted'
                if self.act_advanced_id and self.state == 'posted':
                    self.act_advanced_id.state = 'advanced'
    def _inverse_address(self):
        pass

    @api.depends('partner_id')
    def _compute_address(self):
        for rec in self:
            if rec.partner_id:
                rec.address = f"{rec.partner_id.street if rec.partner_id.street else ''}"
            else:
                rec.address = ""

    description = fields.Char('Nội dung giao dịch')

    # @api.onchange('amount')
    # def onchange_amount_total(self):
    #     tong_tien = self.amount
    #     if self.form_of_allocation == 'auto' and self.payment_type_detail == 'follow_detail_invoice':
    #         danh_sach_so_tien = [data for data in self.detail_account_payment_invoice_ids]
    #         for so_tien in danh_sach_so_tien:
    #             if tong_tien <= 0:
    #                 break
    #             so_tien_fill = min(so_tien.amount_redisual, tong_tien)
    #             so_tien.value = so_tien_fill
    #             tong_tien -= so_tien_fill
    #     if self.form_of_allocation == 'manual' and self.payment_type_detail == 'follow_detail_invoice':
    #         danh_sach_so_tien = [data for data in self.detail_account_payment_invoice_ids]
    #         for so_tien in danh_sach_so_tien:
    #             if so_tien.chosing:
    #                 if tong_tien <= 0:
    #                     break
    #                 so_tien_fill = min(so_tien.amount_redisual, tong_tien)
    #                 so_tien.value = so_tien_fill
    #                 tong_tien -= so_tien_fill

    @api.onchange('partner_id', 'payment_type_detail', 'type_pay','form_of_allocation','amount')
    def onchange_partner_id(self):
        self.detail_account_payment_invoice_ids = False
        if self.payment_type_detail == 'follow_detail_invoice':
            if self.type_pay == 'inbound':
                domain = [('partner_id', '=', self.partner_id.id), ('payment_state', 'not in', ['paid', 'in_payment']), ('move_type', 'in', ['out_invoice'])]
            else:
                domain = [('partner_id', '=', self.partner_id.id), ('payment_state', 'not in', ['paid', 'in_payment']), ('move_type', 'in', ['in_invoice'])]
            partner_invoices = self.env['account.move'].search(domain, order='id ASC')
            vals_list = []
            if partner_invoices:
                for inv in partner_invoices:
                    account_id = False
                    for line in inv.line_ids:
                        if line.debit != 0 and self.type_pay == 'inbound':
                            account_id = line.account_id.id
                        if line.credit != 0 and self.type_pay == 'outbound':
                            account_id = line.account_id.id
                    vals_list.append({
                        'chosing': True if self.form_of_allocation == 'auto' else False,
                        'payment_synthetic_id': self.id,
                        'move_id': inv.id,
                        'partner_id': self.partner_id.id,
                        'account_id': account_id,
                    })
                datas = self.env['detail.acccount.payment.invoice'].create(vals_list)
                tong_tien = self.amount
                danh_sach_so_tien = [data for data in datas]
                if self.form_of_allocation == 'auto':
                    for so_tien in danh_sach_so_tien:
                        if tong_tien <= 0:
                            break

                        so_tien_fill = min(so_tien.amount_redisual, tong_tien)
                        so_tien.value = so_tien_fill
                        tong_tien -= so_tien_fill
    def button_open_account_payment(self):
        return {
            'name': _('Thanh toán'),
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'domain': [('synthetic_id', '=', self.id)]
        }

    def button_open_account_move(self):
        return {
            'name': _('Bút toán'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'domain': [('synthetic_id', '=', self.id)]
        }

    def action_create_tax(self):
        for rec in self.detail_account_payment_partner_ids:
            if rec.tax:
                for ta in rec.tax:
                    self.env['detail.acccount.payment.partner'].sudo().create({
                        'description': rec.description,
                        'partner_id': rec.partner_id.id,
                        'account_id': ta.invoice_repartition_line_ids.filtered(lambda i: i.account_id).account_id.id,
                        'value': (rec.value * ta.amount)/100,
                        'department_id': rec.department_id.id,
                        'analytic_account_id': rec.analytic_account_id.id,
                        'indenture_id': rec.indenture_id.id,
                        'payment_synthetic_id': self.id
                    })
                    self.env['vat.gtgt'].sudo().create({
                        'synthetic_id': self.id,
                        'ref': rec.description,
                        'move_group': 'private use',
                        'vendor': rec.partner_id.id,
                        'tax_code': rec.partner_id.vat,
                        'total_amount_before_tax': rec.value,
                        'tax': ta.id,
                        'amount_tax': rec.value * ta.amount/100,
                        'account_id': ta.invoice_repartition_line_ids[0].account_id.id

                    })

