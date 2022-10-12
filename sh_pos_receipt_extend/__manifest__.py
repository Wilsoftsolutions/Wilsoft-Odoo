# Part of Softhealer Technologies.
{
    "name": "Point Of Sale Extended Receipt",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "point of sale",
    "summary": "Point Of Sale Receipt, POS Customizable Receipt, Point Of Sale Custom Receipt, Point Of Sale Barcode Receipt, Point Of Sale QRCode On Receipt, POS Invoice Number Receipt, POS Receipt,Invoice Number On Receipt, QRCode Receipt, Barcode Receipt Odoo ",
    "description": """This POS module allows you to customize the receipt as per your choice. You can display Barcode or QRCode, invoice number & customer details(name, address, mobile number, phone number & email) in the POS order receipt.""",
    "version": "14.0.10",
    "depends": ["base", "web", "point_of_sale"],
    "application": True,
    
    
    "data": [
        'views/pos_config_settings.xml',
#         'views/sh_pos_receipt_extend.xml',
#         'views/assets.xml',
    ],
    "qweb": ["static/src/xml/pos.xml"],
    "auto_install": False,
    "installable": True,
    "license": "OPL-1",
    "images": ["static/description/background.png", ],
    "price": 20,
    "currency": "EUR"
}
