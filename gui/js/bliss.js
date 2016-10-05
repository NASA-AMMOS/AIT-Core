(function (window, document, undefined) {

    window.oco3     || (window.oco3     = { });
    window.oco3.cmd || (window.oco3.cmd = { });
    window.oco3.tlm || (window.oco3.tlm = { });

    window.oco3.cmd.dict = { };
    window.oco3.tlm.dict = { };
    window.oco3.tlm.evrs = { };

    window.oco3.cmd.typeahead = { dict: { }, hist: { } };

    TlmFields = [ ];

    $.getJSON('/config/cmd', function (data) {
        window.oco3.cmd.dict = data;

        var tok = function (str) {
            return str ? str.split('_') : [];
        };

        window.oco3.cmd.typeahead.dict = new Bloodhound({
            datumTokenizer: tok,
            queryTokenizer: tok,
            local: $.map(data, function (value, key) { return value.name; })
        });

        window.oco3.cmd.typeahead.hist = new Bloodhound({
            datumTokenizer: tok,
            queryTokenizer: tok,
            prefetch: { url: '/cmd/hist.json', cache: false }
        });

        $('#command').typeahead({
            highlight: true,
        },
        {
            name:      'cmd-hist',
            limit:     10,
            source:    window.oco3.cmd.typeahead.hist,
            templates: { header: '<h4 class="typeahead-heading">History</h4>' }
        },
        {
            name:      'cmd-dict',
            limit:     10,
            source:    window.oco3.cmd.typeahead.dict,
            templates: { header: '<h4 class="typeahead-heading">Dictionary</h4>' }
        });
    });

    $.getJSON('/config/evr', function (data) { window.oco3.tlm.evrs = data; });

    $.getJSON('/config/tlm', function (data) {
        window.oco3.tlm.dict = data;

        var tlm = data.OCO3_1553_EHS.fields;

        TlmFields = [ ].concat(
            $.map(tlm, createTlmDefn)
        );
    });


    TlmDefn = function (obj) {
        this.name    = obj.name;
        this.pdt     = obj.type.pdt;
        this.format  = obj.type.format;
        this.mask    = obj.mask;
        this.type    = obj.type.name;
        this.enum    = obj.enum;
        this.shift   = 0;
        this.le      = this.format.length > 0 && this.format[0] === '<';
        this.bytes   = obj.bytes;

        // Bytes can be either one integer or an array, all we need is the head
        if (obj.bytes instanceof Array) {
            this.offset = obj.bytes[0];
        }
        else {
            this.offset = obj.bytes;
        }

        if (this.format.length > 0 &&
            this.format[0] === '<' || this.format[0] === '>') {
            this.format = this.format.substr(1);
        }

        if (typeof obj.mask !== 'undefined' && obj.mask !== null) {
            while (obj.mask !== 0 && (obj.mask & 1) === 0) {
                this.shift += 1;
                obj.mask  >>= 1;
            }
        }
    };

  // The number milliseconds from January 1, 1970, 00:00:00 to
  // January 6, 1980, 00:00:00
    var GPSEpoch = 315964800000;
    TlmDefn.prototype = {
        get: function (view) {
            var value = null;

            switch (this.format) {
                case 'b': value = view.getInt8   (this.offset, this.le); break;
                case 'B': value = view.getUint8  (this.offset, this.le); break;
                case 'h': value = view.getInt16  (this.offset, this.le); break;
                case 'H': value = view.getUint16 (this.offset, this.le); break;
                case 'i': value = view.getInt32  (this.offset, this.le); break;
                case 'I': value = view.getUint32 (this.offset, this.le); break;
                case 'f': value = view.getFloat32(this.offset, this.le); break;
                case 'd': value = view.getFloat64(this.offset, this.le); break;
                default:  break;
            }

            if (typeof this.mask !== 'undefined' && this.mask !== null) {
                value &= this.mask;
            }

            if (this.shift > 0) {
                value >>= this.shift;
            }

            // If enumeration exists, display that value
            if (typeof this.enum !== 'undefined') {
                return this.enum[value];
            }

            return value;
        }
    };


    CmdType = function (obj) {
        TlmDefn.call(this, obj);
    };

    CmdType.prototype = {
        get: function (view) {
            var value = TlmDefn.prototype.get.call(this, view);

            if (value === 0) {
                value = 'N/A';
            }
            else if (window.oco3.cmd.dict[value] !== undefined) {
                value = window.oco3.cmd.dict[value].name;
            }

            return value;
        }
    };


    EVRType = function (obj) {
        TlmDefn.call(this, obj);
    };

    EVRType.prototype = {
        get: function (view) {
            var value = TlmDefn.prototype.get.call(this, view);
      
            // Handle EVR16 Complex type
            if (window.oco3.tlm.evrs[value] !== undefined) {
                value = window.oco3.tlm.evrs[value];
            }

            return value;
        }
    };


    Time8Type = function (obj) {
        TlmDefn.call(this, obj);
    };

    Time8Type.prototype = {
        get: function (view) {
            return TlmDefn.prototype.get.call(this, view) / 256.0;
        }
    };


    Time32Type = function(obj) {
        TlmDefn.call(this, obj);
    };

    Time32Type.prototype = {
        get: function (view) {
            var tv_sec = TlmDefn.prototype.get.call(this, view);
            return new Date(GPSEpoch + (tv_sec * 1000));
        }
    };


    Time40Type = function(obj) {
        TlmDefn.call(this, obj);
    };

    Time40Type.prototype = {
        get: function (view) {
            return TlmDefn.prototype.get.call(this, view);
        }
    };


    Time64Type = function(obj) {
      TlmDefn.call(this, obj);
    };

    Time64Type.prototype = {
        get: function (view) {
            var tv_sec  = view.getUint32(this.bytes[0], this.le);
            var tv_nsec = view.getUint32(this.bytes[0]+4, this.le);

            return new Date(GPSEpoch + (tv_sec * 1000) + (tv_nsec / 1e6));
        }
    };


    createTlmDefn = function (obj) {
        var defn = null;

        switch (obj.type.name) {
            case 'CMD16':  defn = new CmdType   (obj); break;
            case 'EVR16':  defn = new EVRType   (obj); break;
            case 'TIME8':  defn = new Time8Type (obj); break;
            case 'TIME32': defn = new Time32Type(obj); break;
            case 'TIME40': defn = new Time40Type(obj); break;
            case 'TIME64': defn = new Time64Type(obj); break;
            default:       defn = new TlmDefn   (obj); break;
        }

        if (defn !== null) {
            defn.ui = $('[data-field="' + defn.name + '"]');
        }

        return defn;
    };


    updateUI = function (view) {
	var time = TlmDefn.prototype.get.call(TlmFields[119], view);
	time     = GPSEpoch + time * 1000;
	console.log(time);

        for (var n = 0; n < TlmFields.length; ++n) {
            var defn = TlmFields[n];

            try {
                if (defn.ui.length > 0) {
                    var value  = defn.get(view);
                    var format = defn.ui.data('format');
                    if (format !== undefined) {
                        if (defn.type.indexOf('TIME', 0) === 0) {
                            value = strftime.utc()(format, value);
                        }
                        else {
                            value = sprintf(format, value);
                        }
                    }
                    else if (defn.format === 'd' || defn.format === 'f') {
                        value = value.toExponential(5);
                    }
                    defn.ui.text(value);

                    var series = defn.ui.data('plot-series');
		    if (series !== undefined) {
		        var shift = series.data.length > 600;
		        series.addPoint([time, value], true, shift);
		    }
                }
            } catch(e) {
                defn.ui.text('DICT_ERROR');
                console.error(e.message);
            }
        }
    };

    window.oco3.tlm.updateUI = updateUI;

    /*
     * Handle removal of BSC handlers
     *
     * Calls backend service for removing of selected handler 
     * and handles UI alerts for success/failure.
     */
    removeBSCHandler = function(event) {
      name_div = $(event.target).siblings()[0]
      name = name_div.innerText

      $(name_div).addClass('btn-warning')
      $(event.target).html('Removing ...')
      $(event.target).addClass('disabled')

      $.post('/bsc/remove', {name: name})
          .fail(function() {
            $(event.target).html('ERROR: Unable to remove handler')
            $(name_div).removeClass('btn-warning').addClass('btn-danger').delay(500).queue(function(next) {
                $(this).removeClass('btn-danger')
                $(this).dequeue();
            })
          })
          .done(function() {
              $(event.target).delay(500).queue(function(n){
                  $(this).parent().remove()
                  $(this).dequeue();
              })
          });

    }

    /*
     * Update BSC handlers list
     *
     * Query backend services for a list of running handlers,
     * generate HTML structure, and set event listeners.
     */
    updateBSCHandlerList = function() {
        $.getJSON('/bsc/handlers', function(data) {
            data = data['capturers']
            var handlers = []
            $.each(data, function(h) {
                h = data[h]
                handlers.push(
                  "<li class='row bsc-handler-row'>" +
                      "<div class='col-sm-2 btn disabled'>" +
                          h[0] +
                      "</div>" +
                      "<div class='col-sm-2 btn text-danger remove-link'>" +
                          "&times; Remove" +
                      "</div>" +
                  "</li>");
            })

            $('#bsc-handlers').html($("<ul/>", {html: handlers.join(""), class: 'list-unstyled'}))
            $('.remove-link').click(removeBSCHandler);
        });
    };

    /*
     * Set custom form submit for BSC handler creation.
     */
    $('#form-bsc').submit(function(e) {
        e.preventDefault();
        var handler_name = $('#handler-name').val()
        $('#handler-name').val('')
        $.post('/bsc/create', {name: handler_name})
            .fail(function() {
              $('#form-bsc').addClass('has-error').delay(1000).queue(function() {
                  $(this).removeClass('has-error')
                  $(this).dequeue();
              })
            })
            .done(function() {
              $('#form-bsc').addClass('has-success').delay(1000).queue(function() {
                  $(this).removeClass('has-success')
                  $(this).dequeue();
              })
            });

        updateBSCHandlerList();
    });
})(window, document);
