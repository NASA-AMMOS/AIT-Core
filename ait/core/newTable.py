from ait.core import table, log


class NewFSWTabDict(table.FSWTabDict):
    def load(self):
        log.info('Starting the table load() from the extended FSWTabDict class, using file: {}'.format(self.filename))
        return super(NewFSWTabDict, self).load()

    def create(self):
        log.info('Starting the table create() from custom extension class')
        return super(NewFSWTabDict, self).create()

    def custom():
        log.info("Test of a unique method defined in an extension.")
