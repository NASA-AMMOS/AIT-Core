import ait.core
import ait.core.server


class ZmqConfig:
    """
    Configuration methods associated with ZeroMQ
    """
    @staticmethod
    def get_xsub_url():
        return ait.config.get("server.xsub", ait.SERVER_DEFAULT_XSUB_URL)

    @staticmethod
    def get_xpub_url():
        return ait.config.get("server.xpub", ait.SERVER_DEFAULT_XPUB_URL)
