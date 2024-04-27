from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    synthetic_id = fields.Many2one('account.synthetic')
