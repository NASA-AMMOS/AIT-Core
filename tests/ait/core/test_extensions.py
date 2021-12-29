import os, sys, yaml, platform, pytest, logging

import ait
from ait.core import cfg, cmd, util

@pytest.fixture()
def test_dict():
    CMDDICT_TEST = """
- !Command
  name:      SEQ_ENABLE_DISABLE
  opcode:    0x0042
  arguments:
    - !Argument
      name:  sequence_id
      type:  MSB_U16
      bytes: [0, 1]

    - !Argument
      name:  enable
      type:  U8
      bytes: 2
      enum:
        0: DISABLED
        1: ENABLED
"""
    yield cmd.CmdDict(CMDDICT_TEST)

@pytest.fixture(scope='module')
def extended_config_yaml():
    extendee = 'ait.core.cmd.Cmd'
    extendor = 'tests.ait.core.test_extensions.TruthyCmd'
    cfg=f"""
    default:    
        leapseconds:
            filename: leapseconds.dat

    {sys.platform}:
        ISS:
            bticard: 6

    {platform.node().split(".")[0]}:
        ISS:
            apiport: 1234

    extensions:
        {extendee}: {extendor}

    """
    return cfg

@pytest.fixture(scope='module')
def cfg_from_string(extended_config_yaml):
    def tempFile():    
        from tests.ait.core import TestFile 
        with TestFile(data=extended_config_yaml) as filename:
            config = cfg.AitConfig(filename)
            config.reload()
        return config
    old_cfg = ait.config
    ait.config = tempFile()
    cmd.init_ext()
    yield
    ait.config = old_cfg

@pytest.fixture
def opNames(test_dict):
    names = [i.name for i in test_dict.opcodes.values()]
    return names 
    
class TruthyCmd(cmd.Cmd):
    def encode(self):
        return True

def test_extensions(cfg_from_string, test_dict, opNames):
    op = test_dict.create(opNames[0],0,0)
    truthy_encode = op.encode()
    assert isinstance(truthy_encode, bool)
    assert truthy_encode
