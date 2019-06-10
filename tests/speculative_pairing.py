import threading
import random

ready_list = []
paired_list = []

def pairer():

	while True:
		#check if the ready list has atleast two values and create a hider/seeker pair  
		if len(ready_list) > 1:
			hider = ready_list.pop(0)
			seeker = ready_list.pop(0)

			paired_list.append((hider, seeker))
			print(f"paired: {(hider, seeker)}")

			#don't return, keep on looping
			continue

		else:
			continue	


#run the pairer() function on a separate thread.
pair_thread = threading.Thread(target=pairer, args=())
pair_thread.start()

#ask for user input to simulate recieving a 'ready command'.
#On user input, get a random number to simulate a client object / user id
while True:
	ready = input("Type anything for ready :) >> ")
	ready_player_id = random.randint(0, 1000)
	ready_list.append(ready_player_id)






