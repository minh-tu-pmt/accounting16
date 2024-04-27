from odoo import api, fields, models
import datetime


class DetailAccountPaymentPartner(models.Model):
    _name = 'detail.acccount.payment.partner'

    payment_synthetic_id = fields.Many2one('account.synthetic', string="Thanh toán")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    account_id = fields.Many2one('account.account', "Tài khoản", domain="[('is_general_account','=', False)]")
    partner_id = fields.Many2one('res.partner','Đối tác')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    company_currency_id = fields.Many2one('res.currency', related='payment_synthetic_id.currency_id')
    base_value = fields.Monetary('Giá trị nguyên tệ', currency_field='company_currency_id')
    value = fields.Monetary('Giá trị', compute="_compute_value", inverse="inverse_value", store=True)
    move_id = fields.Many2one('account.move',string='Hóa đơn')
    tax = fields.Many2many('account.tax', string="Thuế")

    @api.onchange('tax')
    def tax_onchange(self):
        return {'domain': {'tax': [('type_tax_use', '=', 'purchase')]}}

    @api.depends('payment_synthetic_id.rate_currency', 'base_value')
    def _compute_value(self):
        for rec in self:
            if rec.company_currency_id != rec.currency_id:
                rec.value = rec.base_value * rec.payment_synthetic_id.rate_currency
            else:
                rec.value = rec.value

    def inverse_value(self):
        pass


    description = fields.Char('Diễn giải', store=True)
    department_id = fields.Many2one('hr.department', 'Phòng ban')

    analytic_account_id = fields.Many2one('account.analytic.account', string="Tài khoản phân tích")

    indenture_id = fields.Many2one('act.indenture', 'Mã khế ước')

    fee_group_id = fields.Many2one('fee.group', 'Khoản mục chi phí')

class DetailAccountPayment(models.Model):
    _name = 'detail.acccount.payment.invoice'

    chosing = fields.Boolean('Chọn')

    indenture_id = fields.Many2one('act.indenture', 'Danh mục khế ước')

    payment_synthetic_id = fields.Many2one('account.synthetic', string="Thanh toán")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    move_id = fields.Many2one('account.move', string='Hóa đơn', readonly=True)
    origin = fields.Char('Số hóa đơn', related='move_id.name')
    tax = fields.Many2many('account.tax', string="Thuế")
    partner_id = fields.Many2one('res.partner', 'Đối tác', related='move_id.partner_id')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_id', store=True)
    item_fee_id = fields.Many2one('item.fee', string="Khoản mục chi phí")

    company_currency_id = fields.Many2one('res.currency', related='payment_synthetic_id.currency_id')
    amount_invoice = fields.Float('Tiền hóa đơn')

    @api.onchange('chosing')
    def onchange_chosing(self):
        if self.chosing:
            self.value = self.amount_redisual

    @api.depends('move_id')
    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = rec.move_id.currency_id.id if rec.move_id else False

    invoice_date = fields.Date('Ngày hóa đơn', related='move_id.invoice_date')
    amount_redisual = fields.Monetary('Còn phải thanh toán', related='move_id.amount_residual')

    base_value = fields.Monetary('Giá trị nguyên tệ', currency_field='company_currency_id')

    value = fields.Monetary('Giá trị thanh toán', compute="_compute_value", inverse="inverse_value", store=True)

    amount_total_invoice = fields.Monetary('Tiền hóa đơn', related='move_id.amount_total_signed')

    @api.depends('payment_synthetic_id.rate_currency', 'base_value')
    def _compute_value(self):
        for rec in self:
            if rec.company_currency_id != rec.currency_id:
                rec.value = rec.base_value * rec.payment_synthetic_id.rate_currency
            else:
                rec.value = rec.value

    def inverse_value(self):
        pass

    paid = fields.Monetary('Đã thanh toán', compute="compute_paid_amount")

    @api.depends('move_id')
    def compute_paid_amount(self):
        for rec in self:
            if rec.move_id:
                dict_amount_paid = rec.move_id._get_reconciled_info_JSON_values()
                rec.paid = sum([x['amount'] for x in dict_amount_paid])
            else:
                rec.paid = 0

    description = fields.Char('Diễn giải', store=True)
    account_id = fields.Many2one('account.account',string='Tài khoản',domain="[('is_general_account', '=', False)]")
    department_id = fields.Many2one('hr.department', 'Phòng ban')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Tài khoản phân tích')

    @api.depends('payment_synthetic_id.description')
    def _compute_description(self):
        for rec in self:
            rec.description = rec.payment_synthetic_id.description

    def _inverse_field_des(self):
        for rec in self:
            rec.description = rec.description

class DetailsAccountFlExpenditure(models.Model):
    _name = 'detail.acccount.payment.expenditure'

    partner_receiving_money = fields.Char(string='Đơn vị nhận tiền',related='payment_id.partner_id.name')
    num_account = fields.Char(string='Số tài khoản')
    bank = fields.Char(string="Tại ngân hàng")
    province = fields.Char(string='Tỉnh thành')
    content = fields.Char(string='Nội dung' , related='payment_id.ref')
    fee_th = fields.Selection([('empty', 'Trống'), ('fee_inside', 'Phí trong'), ('fee_outside', 'Phí ngoài')],
                              string="Loại thanh toán", required=True)
    payment_id = fields.Many2one('account.payment',string='Thanh toán')
    synthetic_id = fields.Many2one('account.synthetic', string='Phiếu')
