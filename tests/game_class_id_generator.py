class Test:

	def id_generator():
		"""generates a unique game id"""
		count = 0
		while True:
			yield count
			count += 1

	gen = id_generator()		

	def __init__(self):
		self.myid = next(Test.gen)		




testobj = Test()	
testobj2 = Test()

print(testobj.myid)
print(testobj2.myid)
print(testobj2.myid)
print(testobj2.myid)





