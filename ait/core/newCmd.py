from ait.core import cmd, log


class NewCmd(cmd.Cmd):
    def encode(self):
        log.info('We are in an extension of cmd.encode() that will then call the regular cmd.encode().')
        return super(NewCmd, self).encode()

    def custom(self):
        log.info("In a custom() method defined in the NewCmd extended class.")
