
def game_id():
	count = 0
	while True:
		yield count
		count += 1

game_id = game_id()

print(next(game_id))
print(next(game_id))

