import mock
import unittest

import bliss.core
from bliss.core import api, cfg, pcap

class TestCmdAPI(unittest.TestCase):

    @classmethod
    def tearDownClass(self):
        bliss.config.reload()

    def setup(self):
        bliss.config.reload()

    def test_default_cmd_hist_config(self):
        if 'command' in bliss.config:
            del bliss.config._config['command']

        cmd_api = api.CmdAPI(3075)
        self.assertTrue(isinstance(cmd_api._cmd_log, pcap.PCapRolloverStream))
        self.assertEqual(cmd_api._cmd_log._format, cmd_api.CMD_HIST_FILE)
        self.assertEqual(cmd_api._cmd_log._threshold.nbytes, None)
        self.assertEqual(cmd_api._cmd_log._threshold.npackets, None)
        self.assertEqual(cmd_api._cmd_log._threshold.nseconds, 86400)

    @mock.patch('bliss.core.pcap.open')
    def test_no_rollover_cmd_hist_config(self, pcap_open_mock):
        bliss.config._config['command'] = {
            'history': {
                'filename': 'fakefile.pcap',
                'rollover': {
                    'enable': False
                }
            }
        }
        cmd_api = api.CmdAPI(3075)
        self.assertTrue(pcap_open_mock.called)
        self.assertEqual(pcap_open_mock.call_args[1]['rollover'], False)

    def test_no_default_nseconds_cmd_hist_config(self):
        bliss.config._config['command'] = {
            'history': {
                'filename': 'fakefile.pcap',
                'rollover': {
                    'nseconds': 15
                }
            }
        }
        cmd_api = api.CmdAPI(3075)
        self.assertEqual(
            cmd_api._cmd_log._threshold.nseconds,
            bliss.config.get('command.history.rollover.nseconds')
        )

        bliss.config._config['command'] = {
            'history': {
                'filename': 'fakefile.pcap',
                'rollover': {
                    'npackets': 2
                }
            }
        }
        cmd_api = api.CmdAPI(3075)
        self.assertEqual(cmd_api._cmd_log._threshold.nseconds, None)
        self.assertEqual(
            cmd_api._cmd_log._threshold.npackets,
            bliss.config.get('command.history.rollover.npackets')
        )
