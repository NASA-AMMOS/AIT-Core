#!/usr/bin/env python

import argparse
import datetime as dt
import os.path
import sys

from ait.core import log

"""
Convert MPS Seq files to AIT formatted sequence files
"""

VALID_HEADER_KEYS = ["gap", "on_board_filename", "on_board_path", "upload_type"]


def extract_seq_header(input_file):
    """Extract Seq file header setting values

    Seq files can start with a header specifying the values for configurable
    attributes. This extracts those values and returns key=value pairs as
    a dictionary.

    Note, this reads lines from the open input file handle until it encounters
    a line not starting with a comment indicator ';'. Ensure the file handle
    points to the beginning of the SEQ file.

    Args:
        input_file: (file handle) The open file handle from which lines
        should be read.

    Returns:
        Dictionary containing the key=value pairs from the header
    """
    header = {}
    while True:
        line = input_file.next()
        if not line.startswith(";"):
            break

        line = line.split(";")[-1]
        if line.index("=") != -1:
            line = line.split("=")

            if line[0] in VALID_HEADER_KEYS:
                header[line[0]] = line[1]

    return header


def decode_sequence_time(time, prev_time=None):
    """Decode a MPS Seq time into a datetime object

    Decode an absolute or relative time MPS Seq command time string into
    an absolute time datetime object. If a relative command time is passed
    a previous time must be supplied from which the absolute time should
    be calculated.

    Args:
        time: (string) A MPS Seq command time string to convert into
            a datetime object.

        prev_time: (datetime) A datetime object from which a relative time
            command time will be calculated. Required if `time` is a
            relative command time.

    Returns:
        A datetime object representing the time string

    Raises:
        TypeError: If prev_time is not supplied or is not a datetime object
            and time is a relative command time.

        ValueError: If time has a time code other than `A` or `R`.
    """
    time_code, time = time[0], time[1:]

    if "." not in time:
        time += ":000"
    else:
        time = time.replace(".", ":")

    if time_code == "A":
        converted_time = dt.datetime.strptime(time, "%Y-%jT%H:%M:%S:%f")
    elif time_code == "R":
        if not prev_time or not isinstance(prev_time, dt.datetime):
            msg = (
                "Previous time not specified or incorrect format provided "
                "when given a relative command"
            )
            log.error(msg)
            raise TypeError(msg)

        if "T" in time:
            t_split = time.split("T")
            days, dur = int(t_split[0]), t_split[1]
            hours, mins, secs, msecs = [int(i) for i in dur.split(":")]
        else:
            days = 0
            hours, mins, secs, msecs = [int(i) for i in time.split(":")]

        converted_time = prev_time + dt.timedelta(
            days=days, hours=hours, minutes=mins, seconds=secs, milliseconds=msecs
        )
    else:
        msg = 'Invalid time code "{}" in sequence time'.format(time_code)
        log.error(msg)
        raise ValueError(msg)

    return converted_time


def convert_sequence(input_file, output_file_path):
    """Convert a MPS Seq file into absolute and relative time AIT sequences

    Args:
        input_file: (file object) Input MPS Seq file
        output_file_path: (string) Output file path excluding file extension.
            This path / name will be used to write an Relative Time Sequence
            (RTS) and Absolute Time Sequence (ATS) version of the sequence.
    """
    rts_path = output_file_path + "_rts.txt"
    ats_path = output_file_path + "_ats.txt"
    rts_out = open(rts_path, "w")
    ats_out = open(ats_path, "w")

    prev_time = None

    for line in input_file:
        if line.startswith(";"):
            continue

        clean_line = line.split(";")[0].strip()
        clean_line = clean_line.replace('"', "")
        clean_line = clean_line.replace(",", "")
        split_line = clean_line.split(" ")
        time, command = split_line[0], split_line[1:]

        time = decode_sequence_time(time, prev_time)
        if prev_time is None:
            prev_time = time

        ats_out.write(
            "{} {}\n".format(time.strftime("%Y-%m-%dT%H:%M:%S.%f"), " ".join(command))
        )

        time_delta = time - prev_time
        second_offset = "{}.{}".format(
            int(time_delta.total_seconds()), time_delta.microseconds * 1000
        )
        rts_out.write("{} {}\n".format(second_offset, " ".join(command)))

        prev_time = time

    rts_out.close()
    ats_out.close()


if __name__ == "__main__":
    log.begin()

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("inputseq", help="MPS Seq formatted input file")

    parser.add_argument(
        "-o",
        "--output-name",
        help=(
            "Output file path/name for converted sequence. This should not "
            "include a file extension. File extension and ATS/RTS "
            "identifier will be added automatically. Output name preference "
            "is in order of this argument's value, MPS Seq header's "
            "'on_board_filename' value, or default 'seq_out'."
        ),
    )

    args = parser.parse_args()

    in_file = args.inputseq
    if not os.path.exists(in_file):
        log.error("Input MPS Sequence file does not exist.")  # type: ignore
        sys.exit(1)

    with open(in_file, "r") as input_file:
        seq_header = extract_seq_header(input_file)

    out_file = "seq_out"
    seq_header_outpath = seq_header.get("on_board_filename", None)
    if args.output_name:
        out_file = args.output_name.strip()
    elif seq_header_outpath:
        out_file = seq_header_outpath.split(".")[0].strip()

    with open(in_file, "r") as input_file:
        convert_sequence(input_file, out_file)

    log.end()
