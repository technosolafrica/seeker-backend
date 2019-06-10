import json
import copy
import logging
import logging.config

#set up logging 

#load logging configuration 
with open("logs/logging_configuration.json", 'r') as f:
	log_config_dict = json.load(f) 

logging.config.dictConfig(log_config_dict)
logger = logging.getLogger(__name__) #custom logger



#......app code starts here....... 

#a dictionary of current websocket connections. contents: {websocket : [uuid, username]}
websocket_connections = {}

#a list of players that are ready for a match 
ready_clients_list = []

# a mapping of client id with the connection socket.contents: {uuid: websocket}
client_id_dict = {}

#a mapping of unique game ids to respective game objects. contents : {gameid : gameobj}
game_id_dict = {} 


#all commands defined in the platform protocol

platform_commands = {
		'setuuid' : 'cmd_setuuid',
		'pairresult' : 'cmd_pairresult',
		'pairingtimeout': 'cmd_pairingtimeout',
		'ready' : 'cmd_ready',
		'submit' : 'cmd_submit',
		'result' : 'cmd_result',
		'pending' : 'cmd_pending',
		'noresult' : 'cmd_noresult'
	}

def notify_client(client_socket, msg):
	"""sends notifications to clients by
	writing to their sockets"""
	client_socket.write_message(msg)

def command_dispatcher(client_socket, cmd, data=None):
	"""maps a recieved command to handler function(s) that knows how to 
	handle the commad.

	client_socket - the client connection's websocket object
	cmd- the command issued by the client
	data - the data sent by the client. This is optional since some commands
		   will not be accompanied by any other data.	
	"""
	if cmd == platform_commands['setuuid']:
		set_userid_handler(client_socket, data, client_id_dict)
		register_new_sock(client_socket, data, websocket_connections)
		

	elif cmd == platform_commands['ready']:

		#register submitted client name (expected to be part of the data recieved)
		register_username(client_socket, data, websocket_connections)
		
		#add client to ready to play list
		ready_client_handler(client_socket, ready_clients_list)

		#pair the client
		logger.info(f"Finding a pair for {client_socket}")
		pair = client_pairer(client_socket, ready_clients_list)

		if pair:
			pair1 = websocket_connections[pair[0]][1]
			pair2 = websocket_connections[pair[1]][1] 
			logger.info(f"Successfully Paired: [{pair1} vs {pair2}]")
		else:
			logger.info(f"Couldn't find a pair for {client_socket}. Waiting for other players.")				

		#initialize game
		initialize_game(pair)	

	elif cmd == platform_commands['submit']:
		
		#extract recieved client data
		try:
			gameid = data['gameid']
			client_move = data['move']
			client_role = data['role']
		
		#handle error and return!
		except KeyError as e:
			
			#create an error message
			error_msg = f"""An expected key is missing in the client data submitted for command {cmd}.\nThe client data recieved: {data}"""

			#log the error message to the server	
			logger.exception(error_msg)

			#prepare json data to send to client followng the error
			error_msg_json = json.dumps(
					{ 
					'command' : platform_commands['noresult'],
					'reason' : error_msg
					}
				)

			#send error message to client
			notify_client(client_socket, error_msg_json)	

			return None

		#get the game instance.
		try:
			logger.debug("THE GAME ID DICTIONARY " + str(game_id_dict))
			game = 	game_id_dict[gameid] #get the game instance

		#the game id is nonexistent! Handle the error	
		except KeyError as e:
			#create an error message
			error_msg = f"The game id: {gameid} is non existent."

			#log the error message to the server	
			logger.exception(error_msg)	

			#prepare json data to send to client followng the error
			error_msg_json = json.dumps(
					{ 
					'command' : platform_commands['noresult'],
					'reason' : error_msg
					}
				)

			#send error message to client
			notify_client(client_socket, error_msg_json)	

			return None

		#proceed to call the submit command handler
		game.set_move(client_move, client_role)

def set_userid_handler(client_socket, data, client_id_dict):
	"""
	sets a unique user id for a client object.
	for existing users, replaces old 'websocket'
	data : a dictionary with data. Expects a uuid string.
	client_socket: a client object
	"""
	try:
		uuid = data['uuid'] #get the uuid from the data dictionary
		client_id_dict[uuid] = client_socket #add the uuid to the client id dictionary
		logger.info(f"successfully set the uuid for {client_socket}")

	except Exception as e:
		logger.exception(f"There was an error setting the uuid for {client_socket}")	

	return client_id_dict

def register_new_sock(client_socket, data, websocket_connections):
	""" 
	adds a new client websocket to the list of currently connected websockets
	client_socket: a client object
	data : a dictionary with client data. Expects a uuid string.	
	websocket_connections: a dictionary of current websocket connections
	"""
	try:
		uuid = data['uuid']
		#set uuid and username('anonymous') for the current websocket connection.
		websocket_connections[client_socket] = [uuid, 'anonymous'] 
		logger.info(f"Successfully registered socket: {client_socket}")

	except Exception as e:
		logger.exception(f"There was an error registering socket: {client_socket}")	

	return websocket_connections

def register_username(client_socket, data, websocket_connections):
	""" registeres a new username"""
	try:
		username = data.get('username', None) #if no username is submitted, set to None
		websocket_connections[client_socket][1] = username
		logger.info(f"Successfully registered username [{username}] for socket: {client_socket}")

	except Exception as e:
		logger.exception(f"There was an error registering username socket username for: {client_socket}")	

	return websocket_connections	

def ready_client_handler(client_socket, ready_clients_list):
	""" 
	adds a client to the list of clients waiting.
	to be paired following a cmd_ready command 
	
	client_socket: A client's websocket object.
	"""

	#membership check to avoid having more than one instance.
	#more than one instance means a client could get paired to themselves.
	if client_socket not in ready_clients_list:
		ready_clients_list.append(client_socket)

		#log information : client added to ready list
		logger.info(f"Added '{websocket_connections[client_socket][1]}' with sock: {client_socket} to ready list")
		print(websocket_connections[client_socket][0])
	else:
		logger.warning(f"{client_socket} already in the ready_clients_list: {ready_clients_list}!")	
	
	return ready_clients_list


def pairing_timeout_handler(client, ready_clients_list):
	"""
	removes a client from the list of clients waiting
	to be paired i.e ready_clients_list. This follows a
	cmd_pairingtimeout 

	client: a websocket object
	ready_clients_list: a list of clients waiting to be paired
	"""

	ready_clients_list.remove(client)



def client_pairer(client, ready_clients_list):
	""" 
	Pairs clients that are ready for a match. 
	Returns a tuple of paired clients if successful else none

	client: a client websocket object
	ready_clients_list: a list of clients ready for a match

	"""
	if len(ready_clients_list) > 1:
		hider = ready_clients_list.pop(0)
		seeker = ready_clients_list.pop(0)

		return (hider, seeker)		

	else:
		return None	


class Game:

	#Class wide properties start here

	def id_generator():
		"""
		a simple game id generator. The id is generated in an incremental
		fashion.e.g 0, 1, 2, 3, 4 etc
		"""
		count = 0
		while True:
			yield count
			count += 1

	#create a game id generator object
	id_generator_object = id_generator()

	#Class Insance properties start here
	def __init__(self, hider, seeker):
		"""
		hider: a socket object for the client with a 'hider' role
		seeker: a socket object for the client with a 'seeker' role
		"""
		self.hider = hider
		self.seeker = seeker
		self.hider_move = None
		self.seeker_move = None
		self.gameid = next(Game.id_generator_object) #using the class'es id_generator_object

	def notify(self, client, data):
		"""
		A utility method that is used to push notifications to clients 
		in a game
		
		client: a websocket object
		data : json data to push to client
		"""
		client.write_message(data)
		

	def pairing_notifier(self):
		"""Notifies clients of their pairing"""

		#a template for pair data to send 
		pair_data_template = {
			'command' : platform_commands['pairresult'], #platform_comands : global dict
			'role' : None,	
			'opponent' : None,
			'gameid' : self.gameid
		}

		#pair_data for role 'hider' 
		hider_pair_data = copy.deepcopy(pair_data_template)
		hider_pair_data['role'] = 'hider'
		hider_pair_data['opponent'] = websocket_connections[self.seeker][1]

		#pair_data for role 'seeker'
		seeker_pair_data = copy.deepcopy(pair_data_template)
		seeker_pair_data['role'] = 'seeker'
		seeker_pair_data['opponent'] = websocket_connections[self.hider][1]


		#clients pair data to json string
		hider_data_json = json.dumps(hider_pair_data)
		seeker_data_json = json.dumps(seeker_pair_data)


		#push data to clients
		self.notify(self.hider, hider_data_json) 
		self.notify(self.seeker, seeker_data_json)


	def timer(self):
		"""
		A match timer that ensures a game finishes within a defined period. Clients
		that don't beat this period in submitting their moves get timed out
		"""
		pass	

	def set_move(self, client_move, client_role):
		"""Registeres a clients move to the game"""
		
		try:
			if type(client_move) == bool:
				if client_role == 'hider': 
					self.hider_move = client_move #set hider move
					logger.debug(f"The hider made a move : {client_move}")

					#if opponent has already played, process the game results
					if self.seeker_move != None:
						self.process_game_results()
						logger.debug("Processed Game Results")
				
				elif client_role == 'seeker':
					self.seeker_move = client_move #set seeker move
					logger.debug(f"The seeker made a move : {client_move}")

					#if opponent has already played, process the game results
					if self.hider_move != None:
						self.process_game_results()
						logger.debug("Processed Game Results")					

				else:
					raise(ValueError(f"Unidentified client role type. Expected 'hider' or 'seeker' but got '{client_role}'."))
			else:
				raise ValueError(f"A client move must be a bool. Type {type(client_move)} was given")		

		except Exception as e:
			logger.exception("An error was encountered when setting a client move:")		
						

	def process_game_results(self):
		"""
		contains the logic on what constitutes a win/loss and picks 
		a winner and a looser
		""" 	
		results_data_template = {
			'command' : platform_commands['result'],
			'outcome' : None
		}

		if self.hider_move == self.seeker_move:

			#SEEKER WON!
			#prepare hider results 
			hider_results = copy.deepcopy(results_data_template) #get a copy of the results data template
			hider_results['outcome'] = False #hider lost so set outcome to False
			hider_results_json = json.dumps(hider_results)

			#prepare seeker results
			seeker_results = copy.deepcopy(results_data_template) #get a copy of the results data template
			seeker_results['outcome'] = True #prediction was correct so set outcome to False
			seeker_results_json = json.dumps(seeker_results)

		else:
			#HIDER WON!
			#prepare hider results 
			hider_results = copy.deepcopy(results_data_template) #get a copy of the results data template
			hider_results['outcome'] = True #hider won so set outcome to False
			hider_results_json = json.dumps(hider_results)

			#prepare seeker results
			seeker_results = copy.deepcopy(results_data_template) #get a copy of the results data template
			seeker_results['outcome'] = False #prediction was incorrect so set outcome to False
			seeker_results_json = json.dumps(seeker_results)

		#Send the results to the clients
		self.notify(self.hider, hider_results_json)	
		self.notify(self.seeker, seeker_results_json)


	def end_game(self):
		"""Ends the game"""	
		pass


def initialize_game(pair):
	"""
	pair: can be either a tuple of paired clients (websocket objects) or None. 

	creates a game instance
	"""
	
	#check for a pair of clients and launch a game
	if pair:
		game_instance = Game(pair[0], pair[1])  

		# update the game id dictionary 
		game_id_dict[game_instance.gameid] = game_instance

		#notify clients of their pairing
		game_instance.pairing_notifier()

		#log information
		logger.debug(f"added new game instance: {game_id_dict}")

	else:
		return None 





