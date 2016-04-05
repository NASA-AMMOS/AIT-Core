#!/bin/sh

mkdir -p simple

# pip download -d simple "git+ssh://git@github.jpl.nasa.gov/bliss/bliss-core.git@0.1.0#egg=bliss-core[tests,docs]"
# pip download -d simple "git+ssh://git@github.jpl.nasa.gov/bliss/bliss-core.git@0.2.0#egg=bliss-core[tests,docs]"
# pip download -d simple "git+ssh://git@github.jpl.nasa.gov/bliss/bliss-core.git@0.3.0#egg=bliss-core[tests,docs]"
# pip download -d simple "git+ssh://git@github.jpl.nasa.gov/bliss/bliss-core.git@0.4.0#egg=bliss-core[tests,docs]"
# pip download -d simple "git+ssh://git@github.jpl.nasa.gov/bliss/bliss-core.git@0.5.0#egg=bliss-core[tests,docs]"
# pip download -d simple "git+ssh://git@github.jpl.nasa.gov/bliss/bliss-core.git@0.6.0#egg=bliss-core[tests,docs]"
# pip download -d simple "git+ssh://git@github.jpl.nasa.gov/bliss/bliss-core.git@0.7.0#egg=bliss-core[tests,docs]"
# pip download -d simple "git+ssh://git@github.jpl.nasa.gov/bliss/bliss-core.git@0.8.0#egg=bliss-core[tests,docs]"
#pip download -d simple "git+ssh://git@github.jpl.nasa.gov/bliss/bliss-core.git@0.9.0#egg=bliss-core[tests,docs]"
pip download -d simple "git+ssh://git@github.jpl.nasa.gov/bliss/bliss-core.git@0.10.0#egg=bliss-core[tests,docs]"

./simple.py simple
