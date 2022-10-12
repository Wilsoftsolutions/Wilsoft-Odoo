odoo.define('de_pos_fbr_connector.receipt', function(require){
    "use strict";
    
    var models = require('point_of_sale.models');
    models.load_fields('pos.order', 'invoice_number');
    
    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        export_for_printing: function(){
            var line = _super_orderline.export_for_printing.apply(this, arguments);
            line.invoice_number = this.invoice_number;
            return line;
        }
    });
    
});