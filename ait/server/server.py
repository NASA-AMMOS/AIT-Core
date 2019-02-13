import sys
import gevent
import gevent.monkey; gevent.monkey.patch_all()

from broker import AitBroker
from stream import PortInputStream
from ait.core import log

# manages plugin gevents
# eventually move config parsing & stream/handler/plugin creation from broker to here and then sent to broker on broker init
# streams/handlers/plugins are attribute of server rather than broker; server notifies broker of clients


class AitServer(object):
    inbound_streams = [ ]
    outbound_streams = [ ]
    ports = [ ]
    plugins = [ ]

    def __init__(self):
        broker = AitBroker()
        self.greenlets = (broker.plugins +
                          broker.inbound_streams +
                          broker.outbound_streams +
                          [broker])

        self.start_all_greenlets()

    def start_all_greenlets(self):
        print("starting greenlets")
        print("all greenlets:", self.greenlets)
        for greenlet in self.greenlets:
            print(greenlet)
            greenlet.start()

        print("joining greenlets")
        gevent.joinall(self.greenlets)


def main():
    server = AitServer()
    print("done creating server")
    try:
        import time

        sle_stream = server.broker.get_stream('sle_data_stream')

        def send():
            while True:
                sle_stream.publish(str(4))
                time.sleep(1)

        gevent.spawn(send).join()

    except KeyboardInterrupt:
        print "Exiting ..."


if __name__ == "__main__":
    main()
