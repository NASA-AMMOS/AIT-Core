# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2021, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.


import pickle


def encode_message(topic, data):
    """Encode a message for sending via 0MQ

    Given a string topic name and a pickle-able data object, encode and prep
    the data for sending via `send_multipart`

    Returns a list of the form:
        [
            Bytes object of String (UTF-8),
            Pickled data object
        ]

    If encoding fails None will be returned.

    """
    try:
        enc = [bytes(topic, "utf-8"), pickle.dumps(data)]
    # TODO: This should be way less generic than Exception
    except Exception:
        enc = None

    return enc


def decode_message(msg):
    """Decode a message received via 0MQ

    Given a message received from `recv_multipart`, decode the components.

    Returns a tuple of the form:
        (
            UTF-8 string
            De-pickled data object
        )

    If decoding fails a tuple of None objects will be returned.
    """
    [topic, message] = msg

    try:
        tpc = topic.decode("utf-8")
        msg = pickle.loads(message)
    # TODO: This should be way less generic than Exception
    except Exception:
        tpc = None
        msg = None

    return (tpc, msg)
