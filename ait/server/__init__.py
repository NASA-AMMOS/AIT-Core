import sys

sys.modules['ait.server'].DEFAULT_XSUB_URL = "tcp://*:5559"
sys.modules['ait.server'].DEFAULT_XPUB_URL = "tcp://*:5560"
