from odoo import api, fields, models


class VatGTGT(models.Model):
    _name = 'vat.gtgt'

    move_id = fields.Many2one('account.move', 'Bút toán')
    ref = fields.Char('Diễn giải', compute='_compute_ref', inverse='_inverse_ref', store=True)
    @api.depends('move_id.ref')
    def _compute_ref(self):
        for rec in self:
            if rec.move_id:
                rec.ref = rec.move_id.ref
            else:
                rec.ref = ''

    def _inverse_ref(self):
        pass

    move_group = fields.Selection([('private use', 'Private'), ('shared', 'Shared'), ('for project', 'For Project'), ('invoice normal', 'Invoice Normal'), ('not invoice', 'Not Invoice')], string="Nhóm hóa đơn", required=True, default='private use')
    sign = fields.Char('Kí hiệu')
    invoice_number = fields.Char('Số hóa đơn', )
    invoice_date = fields.Date('Ngày hóa đơn')
    vendor = fields.Many2one('res.partner','Nhà cung cấp')
    address = fields.Char(compute='_compute_address', string="Địa chỉ", store=True, inverse='_inverse_address')
    payment_id = fields.Many2one('account.payment',string='Thanh toán')
    synthetic_id = fields.Many2one('account.synthetic',string='Phiếu Chi')

    def _inverse_address(self):
        pass

    @api.depends('vendor')
    def _compute_address(self):
        for rec in self:
            if rec.vendor:
                rec.address = (f"{rec.vendor.street if rec.vendor.street else ''} {rec.vendor.street2 if rec.vendor.street2 else ''} "
                               f"{rec.vendor.city if rec.vendor.city else ''} {rec.vendor.state_id.name if rec.vendor.state_id else ''} {rec.vendor.country_id.name if rec.vendor.country_id else ''}")
            else:
                rec.address = ""

    @api.onchange('vendor')
    def onchange_vendor(self):
        if self.vendor:
            self.tax_code = self.vendor.vat

    tax_code = fields.Char('Mã số thuế')

    total_amount_before_tax = fields.Monetary('Tổng tiền trước thuế', required=True)

    currency_id = fields.Many2one('res.currency', related='move_id.currency_id', store=True)

    tax = fields.Many2one('account.tax', 'Thuế', required=True, domain="[('type_tax_use','=','purchase'),('active','=', True)]")
    amount_tax = fields.Monetary('Tiền thuế', compute='_compute_amount_tax')

    @api.depends('total_amount_before_tax')
    def _compute_amount_tax(self):
        for rec in self:
            if rec.tax:
                rec.amount_tax = rec.tax.amount*rec.total_amount_before_tax/100
            else:
                rec.amount_tax = 0
    amount_total = fields.Monetary('Thành tiền', compute='_compute_amount_total')

    @api.depends('total_amount_before_tax','amount_tax')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = rec.total_amount_before_tax + rec.amount_tax

    account_id = fields.Many2one('account.account','Tài khoản', domain="[('is_general_account','=', False)]")
