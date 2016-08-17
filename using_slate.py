import slate
import time

# import timeit
# import cProfile
# import pstats

loaded_doc = list()
IGNORE = 'Data rEvolution \n\n \n\nAbOUt thE LEADING EDGE FORUM \n\n \n\n \n\n \n\n \n\nCSC  LEADING  EDGE  FORUM ' \
		 '\n\n \n\n \n\n \n\n'


def parse_file(fname=None):
	global loaded_doc
	
	if not loaded_doc:
		if fname:
			print 'opening...'
			with open(fname) as f:
				print 'loading into slate...'
				doc = slate.PDF(f)
				loaded_doc = doc
		else:
			print 'Aborted : No file name specified !'
			return False
	return True


def run():
	file_name = 'rev.pdf'
	start = time.clock()
	parse_file(file_name)
	elapsed = time.clock()
	elapsed = elapsed - start
	# print 'DONE in %s sec' % duration
	print 'DONE in %0.3f ms' % elapsed * 1000


def dump():
	run()
	for each in loaded_doc:
		print each
		print '###################################################################################################'
	return loaded_doc
