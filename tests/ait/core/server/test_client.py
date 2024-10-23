# import gevent
# from ait.core.server.broker import Broker
# from ait.core.server.client import TCPInputClient
# from ait.core.server.client import TCPInputServer
# broker = Broker()
# TEST_BYTES = "Howdy".encode()
# TEST_PORT = 6666
# class SimpleServer(gevent.server.StreamServer):
#     def handle(self, socket, address):
#         socket.sendall(TEST_BYTES)
# class TCPServer(TCPInputServer):
#     def __init__(self, name, inputs, **kwargs):
#         super(TCPServer, self).__init__(broker.context, input=inputs)
#     def process(self, input_data):
#         self.cur_socket.sendall(input_data)
# class TCPClient(TCPInputClient):
#     def __init__(self, name, inputs, **kwargs):
#         super(TCPClient, self).__init__(
#             broker.context, input=inputs, protocol=gevent.socket.SOCK_STREAM
#         )
#         self.input_data = None
#     def process(self, input_data):
#         self.input_data = input_data
#         self._exit()
# class TestTCPServer:
#     def setup_method(self):
#         self.server = TCPServer("test_tcp_server", inputs=["server", TEST_PORT])
#         self.server.start()
#         self.client = gevent.socket.create_connection(("127.0.0.1", TEST_PORT))
#     def teardown_method(self):
#         self.server.stop()
#         self.client.close()
#     def test_TCP_server(self):
#         nbytes = self.client.send(TEST_BYTES)
#         response = self.client.recv(len(TEST_BYTES))
#         assert nbytes == len(TEST_BYTES)
#         assert response == TEST_BYTES
#     def test_null_send(self):
#         nbytes1 = self.client.send(b"")
#         nbytes2 = self.client.send(TEST_BYTES)
#         response = self.client.recv(len(TEST_BYTES))
#         assert nbytes1 == 0
#         assert nbytes2 == len(TEST_BYTES)
#         assert response == TEST_BYTES
# class TestTCPClient:
#     def setup_method(self):
#         self.server = SimpleServer(("127.0.0.1", 0))
#         self.server.start()
#         self.client = TCPClient(
#             "test_tcp_client", inputs=["127.0.0.1", self.server.server_port]
#         )
#     def teardown_method(self):
#         self.server.stop()
#     def test_TCP_client(self):
#         self.client.start()
#         gevent.sleep(1)
#         assert self.client.input_data == TEST_BYTES
#     def test_bad_connection(self):
#         self.client.port = 1
#         self.client.connection_reattempts = 2
#         self.client.start()
#         assert self.client.connection_status != 0
