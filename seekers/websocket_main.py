from tornado.websocket import WebSocketHandler
import time
from tornado.ioloop import IOLoop
from game import *
import json


class GameWebSocket(WebSocketHandler):
	"""web sockets handler class"""

	###########################################################REMOVE!!!!!!!!!!!!!!!
	def check_origin(self, origin):
		return True

	def open(self):
		"""called when a connection is opened"""
		print("new client connection")
		json_string = json.dumps(
			{"command": "cmd_ack", "ack": "connection successfull"}
			)
		self.write_message(json_string)
		
	def on_message(self, message):
		"""called when the server recieves a message from the client"""	
		
		#load the recieved json message
		data = json.loads(message)

		#get the command issued by client
		cmd = data['command']

		#pass the command to the command dispatcher
		command_dispatcher(self, cmd, data)


	def on_close(self):
		"""called when the client disconnects"""

		print("client closed connection!")

		#check if client was in ready_clients_list and remove them
		#failure to do this will result to a WebSocketClosed error on attempting
		#to write to the socket.
		if self in ready_clients_list:
			ready_clients_list.remove(self)
			print("client removed from ready_clients_list")


