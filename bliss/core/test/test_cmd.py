import unittest

import bliss
import bliss.core

class BasicCmdTest(unittest.TestCase):
    def test_load_default_dict(self):
        cmd_dict = bliss.core.cmd.getDefaultDict()
        assert type(cmd_dict) == type(bliss.core.cmd.CmdDict())

if __name__ == '__main__':
    unittest.main()
