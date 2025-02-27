import unittest 
from unittest.mock import patch, MagicMock 
import socket 
import sys 
import os 

from client import Client 
from server import Server 

class BasicConnectionTest(unittest.TestCase):
    def test_client_connect_success(self):
        import threading 
        server = Server()
        server.start() 

        # Run server acceptance in a separate thread
        server_thread = threading.Thread(target=lambda: server.accept_connection())
        server_thread.daemon = True # Thread will exit when main program exits 
        server_thread.start() 

        import time 
        time.sleep(0.5)

        client = Client("localhost", 8080)
        connection_result = client.connect()


        self.assertTrue(connection_result)

        if server.socket:
            server.socket.close()

if __name__ == "__main__":
    unittest.main()
        

