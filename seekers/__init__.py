from tornado.web import Application
from tornado.httpserver import HTTPServer
from tornado.options import define, options
from tornado.ioloop import IOLoop
from websocket_main import GameWebSocket


define('port', default='5000', help='port to listen on')

def run():
	# construct our chat app
	app = Application([
		('/', GameWebSocket)
	],
	debug = True

)

	# instantiate a server instance to server our app
	http_server = HTTPServer(app)

	# listen to incoming connections on the specified port
	####################################172.16.40.191
	# http_server.listen(options.port) 
	#######################################192.168.0.26
	http_server.listen(options.port, address='172.16.40.86')
	print(f"Server listening on localhost:{options.port}")

	# initiate the IO loop
	IOLoop.current().start() 

if __name__ == '__main__':
	run()	


