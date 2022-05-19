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



//-----
//Constants

let OBJ_NAMESPACE = "ait-ns";
let OBJ_ROOT = "tlm-dict";
let OBJ_NS_ROOT = OBJ_NAMESPACE+":"+OBJ_ROOT;

//-----
//Defaults

// AIT connection settings
const AIT_HOST_DEFAULT = 'localhost';
const AIT_PORT_DEFAULT = 8082;
//Debug
const DEBUG_ENABLED_DEFAULT = false;
//Full-Field names  (field names contain packet)
const FULL_FIELD_NAMES_DEFAULT = false;

//-----
// State variables for connections, debug, ws-reconnect

let ait_host  = AIT_HOST_DEFAULT;
let ait_post  = AIT_PORT_DEFAULT;
let ait_debug = DEBUG_ENABLED_DEFAULT;

//controls if field names are full (with packet) or not
let full_field_names = FULL_FIELD_NAMES_DEFAULT;

// Web-socket reconnection settings
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


//---------------------------------------------

//Sets config, creates providers for Objects and Composition
//for AIT
function AITIntegration(config) {

    //set values to default
    ait_host  = AIT_HOST_DEFAULT;
    ait_post  = AIT_PORT_DEFAULT;
    ait_debug = DEBUG_ENABLED_DEFAULT;
    full_field_names = FULL_FIELD_NAMES_DEFAULT;

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
        if (config.hasOwnProperty('full_field_names'))
        {
            full_field_names = (config.full_field_names === "true");
        }
    }

    //You will only see these if DEBUG was enabled
    debugMsg("AIT Debug   set to: "+ait_debug);
    debugMsg("AIT Host    set to: "+ait_host);
    debugMsg("AIT Port    set to: "+ait_port);
    debugMsg("Full-Fields set to: "+full_field_names);

    tlmdictPromise  = getDictionary(ait_host, ait_port);

    //AIT Object Provider
    let objectProvider = {
        get: function (identifier) {

            return tlmdictPromise.then(function (dictionary) {

                const id_key = identifier.key.toString();
                let rval = null;

                if (identifier.key === OBJ_ROOT) {

                    //Identifier is Root.
                    //Provide information about the root
                    rval =  {
                        identifier: identifier,
                        name: dictionary.name,
                        type: 'folder',
                        location: 'ROOT'
                    };
                } else if (!id_key.includes(".") ) {

                    //Identifier is packet
                    //Provide information about the packet (which contains fields)
                    rval = {
                        identifier: identifier,
                        name: identifier.key,
                        type: 'folder',
                        location: OBJ_NS_ROOT
                    };
                } else {

                    //Identifier is packet-field
                    //Provide information about the packet-field
                    let measurement = dictionary.measurements.find(function (m) {
                                                 return m.key === identifier.key;});
                    if (measurement != null) {
                        const pkt_fld_array = id_key.split(".");
                        const packet_name = pkt_fld_array[0];
                        const field_name = pkt_fld_array[1];

                        // Include full field name (pkt.fld) or just name (fld)
                        const name_value = full_field_names ? measurement.name : field_name;

                        rval = {
                            identifier: identifier,
                            name: name_value,
                            type: 'telemetry',
                            telemetry: {
                                values: measurement.values
                            },
                            location: OBJ_NS_ROOT
                        };
                    } else {
                        console.warn("AIT-objectProvider received unknown " +
                                     "measurement key: "+id_key)
                        return null;
                    }
                }

                return rval;
            });
        }
    };

    //Composition provides a tree structure, where each packet is a folder
    //containing packet fields telemetry.
    //TODO: Consider another layer for subsystem or other?
    let compositionProvider = {
        appliesTo: function (domainObject) {

            let id_key = domainObject.identifier.key.toString();
            //This applies to our namespace, for folder types,
            //but not when key includes '.' (so packets ok, fields not ok)
            return domainObject.identifier.namespace === OBJ_NAMESPACE &&
                   domainObject.type === 'folder' &&
                   !id_key.includes(".");
        },
        load: function (domainObject) {

            let id_key = domainObject.identifier.key.toString();

            if (id_key === OBJ_ROOT) {
                return tlmdictPromise.then(function (dictionary) {

                    //Top level, so collect all of the Packet names (no fields)

                    //create array of unique packet names (by examining all field names)
                    let keySet = new Set(dictionary.measurements.map(item =>
                                         item.key.substr(0,
                                              item.key.indexOf("."))));
                    let keyArr = [...keySet];

                    //return array of packet-name structs
                    let rval = keyArr.map(function (key) {
                        return {
                            namespace: OBJ_NAMESPACE,
                            key: key
                        };
                    });
                    return rval;
                });
            } else  {
                return tlmdictPromise.then(function (dictionary) {

                    //Collect all fields that are part of the packet identified
                    //by id_key
                    let pkt_fields = dictionary.measurements.filter(function(m) {
                                                return m.key.startsWith(id_key)});

                    //return array of field structs
                    let rval = pkt_fields.map(function (m) {
                        return {
                            namespace: OBJ_NAMESPACE,
                            key: m.key
                        };
                    });
                    return rval;
                });
            }
        }
    };

    return function install(openmct) {

        //Add AIT Root
        openmct.objects.addRoot({
            namespace: OBJ_NAMESPACE,
            key: OBJ_ROOT
        });

        //Add Provider for AIT Objects
        openmct.objects.addProvider(OBJ_NAMESPACE, objectProvider);

        //Add Provider to handle tree structure of telem fields
        openmct.composition.addProvider(compositionProvider);

        //Add telemetry type for AIT fields
        openmct.types.addType('telemetry', {
            name: 'Telemetry Point',
            description: 'AIT Telemetry point',
            cssClass: 'icon-telemetry'
        });
    };
}

//---------------------------------------------

//Historical telemetry
//TODO: support the other OpenMCT historical query parameters
function AITHistoricalTelemetryPlugin() {

    return function install (openmct) {
        let provider = {
            supportsRequest: function (domainObject) {
                return domainObject.type === 'telemetry';
            },
            request: function (domainObject, options) {
                let histUrlRoot = 'http://' + ait_host + ':' + ait_port + '/tlm/history/';
                let histUrl = histUrlRoot + domainObject.identifier.key +
                    '?start=' + options.start + '&end=' + options.end;

                return http.get(histUrl)
                    .then(function (resp) {
                        return resp.data;
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

        let msg_json = JSON.parse(event.data);

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

        web_socket = connectRealtime();

        let provider = {
            supportsSubscribe: function (domainObject) {
                return domainObject.type === 'telemetry';
            },
            subscribe: function (domainObject, callback) {
                debugMsg("Adding realtime subscriber for key "+domainObject.identifier.key);
                web_socket.send('subscribe ' + domainObject.identifier.key);
                listener[domainObject.identifier.key] = callback;
                return function unsubscribe() {
                    debugMsg("Removing realtime subscriber for key "+domainObject.identifier.key);
                    delete listener[domainObject.identifier.key];
                    web_socket.send('unsubscribe ' + domainObject.identifier.key);
                };
            }
        };

        openmct.telemetry.addProvider(provider);
    };
};
