/*
 * Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
 * Bespoke Link to Instruments and Small Satellites (BLISS)
 *
 * Copyright 2019, by the California Institute of Technology. ALL RIGHTS
 * RESERVED. United States Government Sponsorship acknowledged. Any
 * commercial use must be negotiated with the Office of Technology Transfer
 * at the California Institute of Technology.
 *
 * This software may be subject to U.S. export control laws. By accepting
 * this software, the user agrees to comply with all applicable U.S. export
 * laws and regulations. User has the responsibility to obtain export licenses,
 * or other export authority as may be required before exporting such
 * information to foreign countries or providing access to foreign persons.
 */

/*
 * Example functions for AIT integration with OpenMCT. The below code can be
 * used in place of the examples provided in the OpenMCT Tutorial so that
 * AIT telemetry can be viewed in real time.
 *
 * https://github.com/nasa/openmct-tutorial
 *
 * Important Notes and Setup:
 *  - Include the below code into OpenMCT by including this file in the
 *    example index.html file and installing the various components.
 *
 *    <script src="ait_integration.js"></script>
 *
 *
 *    openmct.install(AITIntegration(aitconfig));
 *    openmct.install(AITHistoricalTelemetryPlugin());
 *    openmct.install(AITRealtimeTelemetryPlugin());
 *
 *  - where 'aitconfig' is a JSON dictionary that can contain overrides
 *    for AIT Host ('host'), or AIT Port ('port'), e.g.
 *
 *      aitconfig = {  'host': 'localhost', 'port': 8082 };
 *
 *    or a subset, where default values will be used.
 *
 * How to run:
 *  Assuming the above "Important Notes and Setup" have been handled and
 *  the installation instructions in the OpenMCT Tutorial have been run:
 *
 *  1) Run `ait-server.py` to start the AIT backend server
 *  2) Run `npm start` to run the OpenMCT server
 *  3) Point your browser to localhost:8080
 */

//DEFAULTS
// AIT connection settings
const AIT_HOST_DEFAULT = 'localhost';
const AIT_PORT_DEFAULT = 8082;
//Debug
const DEBUG_ENABLED_DEFAULT = false;

// State variables for connections, debug, ws-reconnect
let ait_host  = AIT_HOST_DEFAULT;
let ait_post  = AIT_PORT_DEFAULT;
let ait_debug = DEBUG_ENABLED_DEFAULT;

let ws_reconnect_enabled = true;
let ws_reconnect_wait_millis = 10000;

// Keep a reference to our promise for tlmdict
let tlmdictPromise = null;


//---------------------------------------------

// Updated OpenMCT endpoint returns a converted version of the original AIT
// telem dict so that OpenMct can ingest it.  As such, we just call http.get
// on that endpoint and return the resulting promise.
function getDictionary(host, port) {

    let tdUrl = 'http://' + host + ':' + port + '/tlm/dict'
    debugMsg("Creating tlmdict promise from "+tdUrl)

    return http.get(tdUrl).then(function (result) {
           return JSON.parse(result.data)
    });

}


//---------------------------------------------

// Prints debug message to console, only if debug is enabled
function debugMsg(msg) {
    if (ait_debug)
        console.log("OpenMct/AIT: "+msg);
}


//---------------------------------------------

//Sets config, creates providers for Objects and Composition
//for AIT
function AITIntegration(config) {


    ait_host  = AIT_HOST_DEFAULT;
    ait_post  = AIT_PORT_DEFAULT;
    ait_debug = DEBUG_ENABLED_DEFAULT;

    //check for configuration overrides
    if (config != null)
    {
        if (config.hasOwnProperty('debug'))
        {
            ait_debug = (config.debug === "true");
        }
        if (config.hasOwnProperty('host'))
        {
            ait_host = config.host;

        }
        if (config.hasOwnProperty('port'))
        {
            //Really Javascript? Gotta jump through THIS hoop??
            ait_port = (Number.isInteger(config.port)) ? config.port :
                       (parseInt(config.port) || AIT_PORT_DEFAULT);
        }
    }

    //You will only see these if DEBUG was enabled
    debugMsg("AIT Debug set to: "+ait_debug);
    debugMsg("AIT Host  set to: "+ait_host);
    debugMsg("AIT Port  set to: "+ait_port);

    tlmdictPromise  = getDictionary(ait_host, ait_port);

    let objectProvider = {
        get: function (identifier) {

            return tlmdictPromise.then(function (dictionary) {
                if (identifier.key === 'spacecraft') {
                    return {
                        identifier: identifier,
                        name: dictionary.name,
                        type: 'folder',
                        location: 'ROOT'
                    };
                } else {
                    let measurement = dictionary.measurements.filter(function (m) {
                        return m.key === identifier.key;
                    })[0];
                    return {
                        identifier: identifier,
                        name: measurement.name,
                        type: 'telemetry',
                        telemetry: {
                            values: measurement.values
                        },
                        location: 'taxonomy:spacecraft'
                    };
                }
            });
        }
    };

    let compositionProvider = {
        appliesTo: function (domainObject) {
            return domainObject.identifier.namespace === 'taxonomy' &&
                   domainObject.type === 'folder';
        },
        load: function (domainObject) {
            return tlmdictPromise
                .then(function (dictionary) {
                    return dictionary.measurements.map(function (m) {
                        return {
                            namespace: 'taxonomy',
                            key: m.key
                        };
                    });
                });
        } //,
        // loadHeirarchy: function (domainObject) {
        //     return tlmdictPromise
        //         .then(function (dictionary) {
        //             domainObject.identifier.key
        //             function checkParent(age) {
        //                 return age >= 18;
        //             }
        //             return dictionary.measurements.map(function (m) {
        //                 return {
        //                     namespace: 'taxonomy',
        //                     key: m.key
        //                 };
        //             });
        //         });
        // }
    };

    return function install(openmct) {
        openmct.objects.addRoot({
            namespace: 'taxonomy',
            key: 'spacecraft'
        });
    
        openmct.objects.addProvider('taxonomy', objectProvider);
    
        openmct.composition.addProvider(compositionProvider);
    
        openmct.types.addType('telemetry', {
            name: 'Telemetry Point',
            description: 'Spacecraft Telemetry point',
            cssClass: 'icon-telemetry'
        });
    };
}

//---------------------------------------------

//Historical telemetry
function AITHistoricalTelemetryPlugin() {

    return function install (openmct) {
        let provider = {
            supportsRequest: function (domainObject) {
                return domainObject.type === 'telemetry';
            },
            request: function (domainObject, options) {
                let histUrlRoot = 'http://' + ait_host + ':' + ait_port + '/tlm/history/'
                let histUrl = histUrlRoot + domainObject.identifier.key +
                    '?start=' + options.start + '&end=' + options.end;
    
                return http.get(histUrl)
                    .then(function (resp) {
                        return resp.data
                    });
            }
        };
    
        openmct.telemetry.addProvider(provider);
    }
}


//---------------------------------------------

//setup for realtime handling, via websockets

let realtimeListeners = {};

//Creates a new websocket to the AIT service.
//This will optionally attempt reconnect upon socket close
let connectRealtime = function()
{
    let socketUrl = 'ws://' + ait_host + ':' + ait_port + '/tlm/realtime';

    debugMsg("Creating new realtime Websocket!");
    let web_socket = new WebSocket(socketUrl);

    web_socket.onmessage = function (event) {

        let now = Date.now();
        let listener = realtimeListeners;

        //support passing log messages
        if (Object.prototype.toString.call(event) === "[object String]" && event.startsWith("log")) {
            debugMsg("WebSocket log message: " + str(event));
            return;
        }

        let msg_json = JSON.parse(event.data)

        //Check that JSON object contains telemetry info
        if (msg_json.hasOwnProperty('packet') &&
            msg_json.hasOwnProperty('data')) {
            let packet = msg_json.packet;
            let data   = msg_json.data;
            for (let p in data) {
                let point = {
                    'id': packet + '.' + p,
                    'timestamp': now,
                    'value': data[p]
                };

                //Broadcast telemetry point to associated listener
                if (listener[point.id]) {
                    debugMsg("Broadcasting realtime telem event for '" + JSON.stringify(point));
                    listener[point.id](point);
                }
            }
        }
    };

    web_socket.onerror = function (event) {
        console.warn("AIT realtime Websocket error: "+JSON.stringify(event))
    };

    web_socket.onclose = function (event) {
        debugMsg("AIT realtime Websocket closed: "+JSON.stringify(event));
        if (ws_reconnect_enabled) {
            debugMsg("AIT realtime Websocket will attempt reconnect after "+ws_reconnect_wait_millis+" ms");
            setTimeout(connectRealtime, ws_reconnect_wait_millis)
        }
    };

    return web_socket;
};

//Realtime Telemetry
function AITRealtimeTelemetryPlugin() {

    return function install(openmct) {

        //attach to listener map declared above
        let listener = realtimeListeners;

        connectRealtime();

        let provider = {
            supportsSubscribe: function (domainObject) {
                return domainObject.type === 'telemetry';
            },
            subscribe: function (domainObject, callback) {
                debugMsg("Adding realtime subscriber for key "+domainObject.identifier.key);
                listener[domainObject.identifier.key] = callback;
                return function unsubscribe() {
                    debugMsg("Removing realtime subscriber for key "+domainObject.identifier.key);
                    delete listener[domainObject.identifier.key];
                };
            }
        };

        openmct.telemetry.addProvider(provider);
    };
};
