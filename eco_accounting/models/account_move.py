from odoo import api, fields, models
import datetime
from odoo.exceptions import AccessError, ValidationError
from datetime import datetime, date


class AccountMove(models.Model):
    _inherit = 'account.move'


    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if 'order_display' in self._context:
            order = self._context.get('order_display')
        res = super(AccountMove, self)._search(args, offset, limit, order, count, access_rights_uid)
        return res

    synthetic_id = fields.Many2one('account.synthetic')

    rate_curr = fields.Float('Tỷ giá', compute='_compute_rate_curr', inverse='_inverse_rate_curr', store=True, digits=(16, 2))


    detail_account_vat_gtgt_ids = fields.One2many('vat.gtgt', 'move_id', string="Thuế giá trị gia tăng đầu vào !")
    detail_acccount_payment_partner_ids = fields.One2many('detail.acccount.payment.partner', 'move_id', string="Chi tiết")

    # Advance settlement

    @api.model
    def _generate_num_adsettlement(self):
        current_date = date.today()  # Use date.today() instead of datetime.date.today()
        year = str(current_date.year)
        month = str(current_date.month).zfill(2)
        records = self.search_count([('create_date', '>=', year + '-' + month + '-01 00:00:00'),
                                     ('create_date', '<=',
                                      year + '-' + month + '-' + str(current_date.day) + ' 23:59:59')])

        sequence_number = str(records + 1).zfill(5)
        return f'QTTU/{year}/{month}/{sequence_number}'

    num_adsettlement = fields.Char(string='Số chứng từ', default=lambda self: self._generate_num_adsettlement())
    partner_setment_id = fields.Many2one('res.partner', string='Nhân viên')
    act_advance_ids = fields.Many2many('act.advance', string="Phiếu đề nghị",
                                       domain=lambda self: self._compute_act_advance_domain())
    description_setle = fields.Char(string='Diễn giải')
    account_sett_id = fields.Many2one('account.account', string='Tài khoản tạm ứng')
    date_request = fields.Date(string='Ngày đề nghị', default=fields.Date.today)
    end_payment = fields.Date(string='Hạn thanh toán', default=fields.Date.today)
    settle_true = fields.Boolean(string="Có phải quyết toán không")
    @api.onchange('partner_id')
    def _compute_act_advance_domain(self):
        if not self.partner_id or not self.partner_id.id:
            return {'domain': {'act_advance_ids': []}}  # Clear domain if partner_id is not set or its id is not set

        partner_ids = [self.partner_id.id]
        advance = self.env['act.advance'].search([('state', '=', 'advanced'), ('person_sugges_id.partner_id', 'in', partner_ids)])

        domain = [('id', 'in', advance.ids)]
        return {'domain': {'act_advance_ids': domain}}

    def check_occurrences(self, lst):
        count_dict = {}

        # Đếm số lần xuất hiện của từng phần tử
        for num in lst:
            if num in count_dict:
                count_dict[num] += 1
            else:
                count_dict[num] = 1

        # Kiểm tra xem có phần tử nào xuất hiện 3 lần không
        for key, value in count_dict.items():
            if value == 2:
                return False

        return True

    @api.model
    def create(self, vals_list):
        res = super(AccountMove, self).create(vals_list)
        if res.move_type == 'entry':
            if res.line_ids and len(res.line_ids) > 2:
                list_group_clause_credit = []
                for x in res.line_ids:
                    if x.group_clause and x.credit:
                        list_group_clause_credit.append(x.group_clause)
                list_group_clause_debit = []
                for x in res.line_ids:
                    if x.group_clause and x.debit:
                        list_group_clause_debit.append(x.group_clause)
                for r in res.line_ids:
                    if not r.group_clause:
                        raise ValidationError('Có nhiều hạch toán nợ/có trong phiếu, vui lòng cập nhập nhóm định khoản!')
                if not self.check_occurrences(list_group_clause_credit) and not self.check_occurrences(list_group_clause_debit):
                    raise ValidationError('Không được hạch toán nhiều nợ nhiều có trong một nhóm định khoản!')
        return res

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        for rec in self:
            if rec.move_type == 'entry':
                if rec.line_ids and len(rec.line_ids) > 2:
                    list_group_clause_credit = []
                    for x in rec.line_ids:
                        if x.group_clause and x.credit:
                            list_group_clause_credit.append(x.group_clause)
                    list_group_clause_debit = []
                    for x in rec.line_ids:
                        if x.group_clause and x.debit:
                            list_group_clause_debit.append(x.group_clause)
                    for r in rec.line_ids:
                        if not r.group_clause:
                            raise ValidationError('Có nhiều hạch toán nợ/có trong phiếu, vui lòng cập nhập nhóm định khoản!')
                    if not self.check_occurrences(list_group_clause_credit) and not self.check_occurrences(list_group_clause_debit):
                        raise ValidationError('Không được hạch toán nhiều nợ nhiều có trong một nhóm định khoản!')
        return res
    # @api.model
    # def _get_default_currency(self):
    #     ''' Get the default currency from either the journal, either the default journal's company. '''
    #     for rec in self:
    #         if rec.move_type == 'entry':
    #
    #
    #     journal = self._get_default_journal()
    #     return journal.currency_id or journal.company_id.currency_id

    @api.depends('currency_id.rate_ids.company_rate')
    def _compute_rate_curr(self):
        for rec in self:
            if self.env.company.currency_id.id == rec.currency_id.id:
                rec.rate_curr = 1
            elif self.env.company.currency_id.id != rec.currency_id.id and rec.currency_id.rate_ids:
                dicts = [
                    {'rate': x.company_rate, "date": x.name} for x in self.currency_id.rate_ids
                ]

                today = datetime.today().date()

                nearest_dict = min(dicts, key=lambda x: abs(x['date'] - today))

                rec.rate_curr = int(nearest_dict['rate'])
            else:
                rec.rate_curr = 0

    @api.onchange('rate_curr')
    def onchange_rate_cur(self):
        if self.move_type == 'entry':
            for line in self.line_ids:
                company = line.move_id.company_id
                balance = line.currency_id.with_context(ratio=line.move_id.rate_curr)._convert(line.amount_currency,
                                                                                               company.currency_id,
                                                                                               company,
                                                                                               line.move_id.date or fields.Date.context_today(
                                                                                                   line))
                line.debit = balance if balance > 0.0 else 0.0
                line.credit = -balance if balance < 0.0 else 0.0

                if not line.move_id.is_invoice(include_receipts=True):
                    continue

                line.update(line._get_fields_onchange_balance())
                line.update(line._get_price_total_and_subtotal())

    def _inverse_rate_curr(self):
        pass


class AccMoveLine(models.Model):
    _inherit = 'account.move.line'

    check_curr = fields.Boolean(compute='_compute_curr_check', store=True)
    department_id = fields.Many2one('hr.department', 'Phòng ban')
    indenture_id = fields.Many2one('act.indenture', 'Mã khế ước')
    group_clause = fields.Char('Nhóm định khoản', default=False)
    item_fee_id = fields.Many2one('item.fee', string="Khoản mục chi phí")

    @api.onchange('currency_id')
    def _onchange_currency(self):
        for line in self:
            company = line.move_id.company_id

            if line.move_id.is_invoice(include_receipts=True):
                line._onchange_price_subtotal()
            elif not line.move_id.reversed_entry_id:
                balance = line.currency_id.with_context(ratio=line.move_id.rate_curr)._convert(line.amount_currency,
                                                                                               company.currency_id,
                                                                                               company,
                                                                                               line.move_id.date or fields.Date.context_today(
                                                                                                   line))
                line.debit = balance if balance > 0.0 else 0.0
                line.credit = -balance if balance < 0.0 else 0.0

    @api.onchange('amount_currency')
    def _onchange_amount_currency(self):
        for line in self:
            company = line.move_id.company_id
            balance = line.currency_id.with_context(ratio=line.move_id.rate_curr)._convert(line.amount_currency,
                                                                                           company.currency_id, company,
                                                                                           line.move_id.date or fields.Date.context_today(
                                                                                               line))
            line.debit = balance if balance > 0.0 else 0.0
            line.credit = -balance if balance < 0.0 else 0.0

            if not line.move_id.is_invoice(include_receipts=True):
                continue

            line.update(line._get_fields_onchange_balance())
            line.update(line._get_price_total_and_subtotal())

    @api.constrains('partner_id', 'account_id')
    def constrains_account_id(self):
        for rec in self:
            if rec.account_id.is_debt_account and not rec.partner_id:
                raise ValidationError(f"Tài khoản {rec.account_id.name} là tài khoản công nợ, vui lòng nhập đối tác !")

    def is_positive_integer(self, value):
        try:
            # Chuyển đổi giá trị thành số nguyên
            n = int(value)
            # Kiểm tra nếu là số nguyên dương
            if n > 0:
                return True
            else:
                return False
        except ValueError:
            # Nếu không thể chuyển đổi thành số nguyên, hoặc nếu là số âm hoặc không phải số
            return False

    @api.constrains('group_clause')
    def group_clause_constrains(self):
        for rec in self:
            if rec.group_clause and not self.is_positive_integer(rec.group_clause):
                raise ValidationError('Phải nhập số nguyên dương cho nhóm định khoản!')

    # @api.onchange('amount_currency')
    # def _onchange_amount_currency(self):
    #     if self.debit and self.amount_currency <0:
    #         raise ValidationError('Vui lòng nhập số dương!')
    #     if self.credit and self.amount_currency >0:
    #         raise ValidationError('Vui lòng nhập số âm!')

    @api.depends('currency_id')
    def _compute_curr_check(self):
        for r in self:
            if r.currency_id.id != self.env.company.currency_id.id:
                r.check_curr = False
            else:
                r.check_curr = True
