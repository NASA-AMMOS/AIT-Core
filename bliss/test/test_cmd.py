import unittest

import bliss

class BasicCmdTest(unittest.TestCase):
    def test_load_default_dict(self):
        cmd_dict = bliss.cmd.getDefaultDict()
        assert type(cmd_dict) == type(bliss.cmd.CmdDict())

if __name__ == '__main__':
    unittest.main()
