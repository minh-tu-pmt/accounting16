from odoo import api, models, fields, SUPERUSER_ID, _
from odoo.exceptions import ValidationError
from datetime import datetime, date\

class ActionLost(models.TransientModel):
    _name = 'act.flow.advanced'

    account_move_id = fields.Many2one('account.move',string="Quyết toán")

    def action_accept_advanced(self):
        return {
            'name': 'Phiếu Chi',
            'type': 'ir.actions.act_window',
            'res_model': 'account.synthetic',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('eco_accounting.form_view_account_synthetic_cashout').id,
            'target': 'current',
        }

    def action_give_back_advanced(self):
        return {
            'name': 'Phiếu thu',
            'type': 'ir.actions.act_window',
            'res_model': 'account.synthetic',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('eco_accounting.form_view_account_synthetic').id,
            'target': 'current',
        }

    def action_reject_advanced(self):
        self.account_move_id.action_post()