odoo.define('payment_ebizcharge.flush_realtime_data', function (require) {
    "use strict";
var core = require('web.core');

var ListView = require('web.ListView');
var viewRegistry = require('web.view_registry');
var ListRenderer = require('web.ListRenderer');
var FormRenderer = require('web.FormRenderer');
var utils = require('web.utils');

var CustomRenderer = ListRenderer.extend({
    destroy: function(){
    var self = this;
    console.log(this.state);
            this._rpc({
            model: self.state.model,
            method: 'from_js',
            args: [1],
        }).then(function (ids) {
        console.log(ids)
        });
        return self._super();
    },
});
var InventoryReportListView2 = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Renderer: CustomRenderer,
    }),

});


FormRenderer.include({
    destroy: function(){
    var self = this;
    let appModels = ['res.partner', 'account.payment', 'batch.processing']
    if (appModels.indexOf(self.state.model) !== -1){
        var res_ids = []
        if(self.state.model === 'batch.processing'){
            utils.traverse_records(this.state['data']['transaction_history_line'], function (record) {
                res_ids.push(record['data']['customer_id']);
            });
        }
        else if(self.state.model === 'account.payment'){
            res_ids.push(self.state.data.partner_id.ref)
        }
        this._rpc({
            model: self.state.model,
            method: 'js_flush_customer',
            args: [self.state.data.id],
            kwargs: {"customers":res_ids},
        });
    }
    return self._super();
    },
});


//ListRenderer.include({
//    destroy: function(){
//    var self = this;
////    debugger
//    let appModels = ['account.move']
//    if (self.state.context.ebiz_batch_process_action === 1){
//        this._rpc({
//            model: "res.partner",
//            method: 'js_flush_customer',
//            args: [0],
//        }).then(function (ids) {
//        console.log(ids)
//        });
//    }
//    return self._super();
//    },
//})
viewRegistry.add('flush_realtime_data', InventoryReportListView2);
return InventoryReportListView2;

});