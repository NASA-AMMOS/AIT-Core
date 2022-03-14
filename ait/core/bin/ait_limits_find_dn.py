#!/usr/bin/env python
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

"""
ait-limits-find-dn

Extract the DN-equivalent value for EU limit trip thresholds

usage:
    > ait-limits-find-dn

This utility requires well-formed telemetry and limits dictionaries. DN thresholds
are brute forced for each limit. Partial limit definitions (i.e., without an
upper and lower error / warn value) are supported. Any missing limit values or
points where a threshold cannot be found for the field's DN-to-EU equation will
be displayed as None in the final table.

Note, "value" limits are not supported by this script and will be skipped. An
example value limit:

    - !Limit
      source: Ethernet_HS_Packet.product_type
      desc: Ethernet Product Type field
      value:
        error: MEM_DUMP
        warn:
          - TABLE_FOO
          - TABLE_BAR
"""

from ait.core import limits
from ait.core import log
from ait.core import tlm


def main():
    dn_limits = {}
    eu_limits = {}
    eu_values = {}

    ld = limits.getDefaultDict()
    td = tlm.getDefaultDict()

    all_vals = [
        [
            "Telem Point",
            "EU lower.error",
            "EU lower.warn",
            "EU upper.warn",
            "EU upper.error",
            "DN lower.error",
            "DN lower.warn",
            "DN upper.warn",
            "DN upper.error",
            "DN to EU LE",
            "DN to EU LW",
            "DN to EU UW",
            "DN to EU UE",
        ]
    ]

    for source in sorted(ld.keys(), key=lambda x: x.split(".")[1]):
        log.info(f"Processing {source}")
        pkt_name, name = source.split(".")

        # Don't support limits specifying individual values. This is usually
        # used to specify enumerations that aren't valid and we don't properly
        # handle those cases.
        if ld[source].value is not None:
            log.warn(f'Skipping unsupported "value" limit {source}')
            continue

        dn_limits.setdefault(name, [None, None, None, None])
        eu_limits.setdefault(name, [None, None, None, None])
        eu_values.setdefault(name, [None, None, None, None])

        if ld[source].lower is not None:
            try:
                eu_limits[name][0] = ld[source].lower.error
            except AttributeError:
                pass

            try:
                eu_limits[name][1] = ld[source].lower.warn
            except AttributeError:
                pass

        if ld[source].upper is not None:
            try:
                eu_limits[name][2] = ld[source].upper.warn
            except AttributeError:
                pass

            try:
                eu_limits[name][3] = ld[source].upper.error
            except AttributeError:
                pass

        values = []

        defn = td[pkt_name]
        data = bytearray(defn.nbytes)
        packet = tlm.Packet(defn, data)
        for dn in range(65536):
            setattr(packet, name, dn)
            eu = getattr(packet, name)

            if eu is not None:
                values.append((dn, eu))

        values.sort(key=lambda pair: pair[1])

        for dn, eu in values:
            for n in range(4):
                if (
                    eu_limits[name][n] is not None
                    and dn_limits[name][n] is None
                    and eu > eu_limits[name][n]
                ):
                    value = dn - 1 if dn > 0 else 0
                    dn_limits[name][n] = value

                    setattr(packet, name, value)
                    eu_values[name][n] = getattr(packet, name)

            if all(dn_limits[name][n] is not None for n in range(4)):
                break

        values = [source]
        values.extend(map(str, eu_limits[name]))
        values.extend(map(str, dn_limits[name]))
        values.extend(map(str, eu_values[name]))
        all_vals.append(values)

    s = [[str(e) for e in row] for row in all_vals]
    lens = [max(map(len, col)) for col in zip(*s)]
    fmt = "\t".join("{{:{}}}".format(x) for x in lens)
    table = [fmt.format(*row) for row in s]
    print("\n".join(table))


if __name__ == "__main__":
    main()
