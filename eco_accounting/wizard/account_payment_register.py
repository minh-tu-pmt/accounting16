from odoo import api, fields, models, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    synthetic_id = fields.Many2one('account.synthetic')

    def action_create_payments(self):
        payments = self._create_payments()
        for rec in payments:
            rec.synthetic_id = self.synthetic_id.id
        if self._context.get('dont_redirect_to_payments'):
            return True

        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        self.synthetic_id.state = 'posted'
        return action

    def _create_payment_vals_from_wizard(self):
        payment_vals = {
            'date': self.payment_date,
            'amount': self.amount,
            'payment_type': self.payment_type,
            'partner_type': self.partner_type,
            'ref': self.communication,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_bank_id': self.partner_bank_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'destination_account_id': self.line_ids[0].account_id.id
        }
        if (not self.currency_id.is_zero(self.payment_difference) and self.synthetic_id and self.synthetic_id.check_currency
                and self.synthetic_id.amount > sum([x.value if x.chosing else 0 for x in self.synthetic_id.detail_account_payment_invoice_ids])):
            move = self.env['account.move'].create({
                'ref': self.writeoff_label,
                'move_type': 'entry',
                'date': self.payment_date,
                'rate_curr': self.synthetic_id.rate_currency,
                'journal_id': self.journal_id.id,
                'currency_id': self.currency_id.id,
                'line_ids':
                    [(0, 0, {
                        'name': self.writeoff_label,
                        'date_maturity': self.payment_date,
                        'currency_id': self.currency_id.id,
                        'debit': abs(self.payment_difference),
                        'credit': 0.0,
                        'partner_id': self.partner_id.id if self.partner_id else False,
                        'account_id': self.journal_id.default_account_id.id,
                        'group_clause': 1
                    }), (0, 0, {
                        'name': self.writeoff_label,
                        'date_maturity': self.payment_date,
                        'currency_id': self.currency_id.id,
                        'debit': 0.0,
                        'credit': abs(self.payment_difference),
                        'partner_id': self.partner_id.id if self.partner_id else False,
                        'account_id': self.writeoff_account_id.id,
                        'group_clause': 1
                    })],
                'synthetic_id': self.synthetic_id.id
            })
        if not self.currency_id.is_zero(self.payment_difference) and self.payment_difference_handling == 'reconcile':
            payment_vals['write_off_line_vals'] = {
                'name': self.writeoff_label,
                'amount': self.payment_difference,
                'account_id': self.writeoff_account_id.id,
                'synthetic_id': self.synthetic_id.id
            }
        return payment_vals
