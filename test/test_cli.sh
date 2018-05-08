#!/bin/bash

set -e

test_help() {
    _script=${1//_/-}
    $_script --help > /dev/null
}

test_ait_cmd_send() {
    ait-cmd-send NO_OP > /dev/null
}

if [ -z $AIT_ROOT ]; then
    AIT_ROOT=../
fi

# loop through all scripts in the bin directory
for script in `find ${AIT_ROOT}/ait/core/bin -type f -name "*.py"`; do
    if [[ "$script" == *__init__* ]]; then
        continue
    fi

    # Build the function name from the script filepath
    scr_name=$(basename $script)
    fx_name=${scr_name%".py"}
    
    if [ "$(type -t test_$fx_name)" != "function" ]; then
        echo "Test for $scr_name does not exist. Checking --help flag."
        echo $fx_name
        test_help $fx_name
    else
        test_$fx_name
    fi

done

#
# main end
####


