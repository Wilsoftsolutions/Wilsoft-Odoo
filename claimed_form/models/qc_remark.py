from odoo import api, fields, models

class QCRemarkModel(models.Model):
    _name = 'qc.remark'
    _rec_name = 'qc_remark'

    qc_remark = fields.Char("QC Remark")



class ClaimRemarkModel(models.Model):
    _name = 'claim.remark'

    name = fields.Char('Claim Remark')