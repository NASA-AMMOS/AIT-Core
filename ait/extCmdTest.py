import ait.core.cmd as cmd
# import ait.core.log as log

cmdDict = cmd.getDefaultDict()
no_op = cmdDict.create('NO_OP')
no_op.encode()
no_op.custom()
