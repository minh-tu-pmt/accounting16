from odoo import api, fields, models
from odoo.osv import expression

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if 'type_journal' in self._context and self._context.get('type_journal') == 'cash':
            journals = self.search([('type','=','cash')])
            if journals:
                args = expression.AND([[('id', 'in', journals.ids)], args])
        if 'type_journal' in self._context and self._context.get('type_journal') == 'bank':
            journals = self.search([('type','=','bank')])
            if journals:
                args = expression.AND([[('id', 'in', journals.ids)], args])
        return super(AccountJournal, self)._name_search(name, args, operator, limit, name_get_uid)