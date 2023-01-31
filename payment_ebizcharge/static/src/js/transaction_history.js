odoo.define('payment_ebizcharge.portal', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.portalSearchPanel = publicWidget.Widget.extend({
    selector: '.o_portal_transaction_history',
    events: {
        'click .search-submit': '_onSearchSubmitClick',
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * @private
     */
    _search: function () {
        var search = $.deparam(window.location.search.substring(1));
        search['search'] = this.$('input[name="search"]').val();
        window.location.search = $.param(search);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSearchSubmitClick: function () {
        this._search();
    },

});

});
