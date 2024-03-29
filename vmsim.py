#!/usr/bin/env python3

# Colby King
# CS1550 Project 3 - VMSim

import sys, getopt
from collections import OrderedDict
import math #for math.log(base, num)



# args: -n, -p, -s

def get_args():
	""" Parses C-style commandline arguments"""
	arguments = {}
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'n:p:s:')
	except getopt.GetoptError as e:
		print(e)
		sys.exit()

	for o, a in opts:
		try:
			if o == '-n':
				arguments['numframes'] = int(a)
			elif o == '-p':
				arguments['pagesize'] = int(a)
			elif o == '-s':
				arguments['mem_split'] = a
		except ValueError as e:
			print("Couldn't parse arg {} into integer".format(a))
			sys.exit()

	arguments['tracefile'] = sys.argv[-1]
	return arguments


def read_trace(args):
	""" Reads the tracefile into a list of PageRef objects """
	with open(args['tracefile']) as tracefile:
		lines = []
		for line in tracefile:
			frm_data = line.strip().split()
			lines.append(PageRef(frm_data[0], frm_data[1], frm_data[2], args['pagesize']))

		return lines

	


class PageRef(object):

	def __init__(self, mode, addr, process_id, size):
		self._addr_str = addr
		self._mode = mode
		self._process_id = int(process_id)
		self._ref = 0
		self._dirty = False if mode == 'l' else True
		self.size = size
		self.offset = int(math.log(1024 * self.size, 2))

	@property
	def addr_str(self):
		"""Returns the associated full hex address as a string"""
		return self._addr_str

	@property
	def addr(self):
		""" returns the decimal value of the hex address"""
		return int(self._addr_str, 16)	

	@property
	def mode(self):
		"""Returns the mode the line read in"""
		return self._mode

	@property
	def ref(self):
		"""Returns the reference bit"""
		return self._ref

	@property
	def dirty(self):
		"""Returns whether PageRef is dirty"""
		return self._dirty
	
	@property
	def process_id(self):
		"""Returns PageRef's associated process id"""
		return self._process_id

	def set_ref_bit(self, ref):
		"""Sets the PageRef's reference bit to provided value"""
		self._ref = ref

	def set_dirty_bit(self):
		"""Sets the PageRef's dirty bit to True"""
		self._dirty = True

	def page_number(self):
		"""Returns the page number given an offset"""
		return self.addr >> self.offset


	def __repr__(self):
		""" For debugging..."""
		return '{}-{}'.format(self.page_number(), self.ref)

	def __str__(self):
		""" For debugging..."""
		return '{}-{}'.format(self.page_number(), self.ref)


class SecondChance(object):
	def __init__(self, size, pagesize, split, offset, pid):
		self.size = size
		self.pagesize = pagesize
		self.split = split
		self.offset = offset
		self.memory = []
		self.index_cache = {}
		self.pid = pid
		self.cur_index = 0
		self._statistics = {
			'accesses': 0,
			'pagefaults': 0,
			'diskwrites':0,
			'size': size,
			'pid': pid
		}

	@property
	def statistics(self):
		return self._statistics
	

	@property
	def space_available(self):
		"""Returns if space is available in Second chance memory implementation"""
		return len(self.memory) < self.size
	

	def update_index_cache(self, old_page, new_page, index):
		"""Updates cache for quick page lookups """

		# delete entry being evicted, if there is one
		if old_page:
			del self.index_cache[old_page.page_number()]
		# Add new page
		self.index_cache[new_page.page_number()] = index

	def evict_and_replace(self, page):
		# maximum loop is a full round-robin
		for i in range(self.size):
			# check if current index should be evicted (front of line)
			if self.memory[self.cur_index].ref == 0:
				old_page = self.memory[self.cur_index]
				# Evict page
				self.memory[self.cur_index] = page
				# Update index cache
				self.update_index_cache(old_page, page, self.cur_index)
				# increment pointer
				self.cur_index = (self.cur_index + 1) % self.size
				return old_page
			else:
				# Otherwise, clear reference bit
				self.memory[self.cur_index].set_ref_bit(0)
			# increment pointer
			self.cur_index = (self.cur_index + 1) % self.size

		# If nothing is found, return index to original pos and return that (FIFO)
		old_page = self.memory[self.cur_index]
		self.memory[self.cur_index] = page
		# update index cache
		self.update_index_cache(old_page, page, self.cur_index)
		self.cur_index = (self.cur_index + 1) % self.size
		return old_page

	def update_statistics(self, pf, diskwrite):
		"""Updates second chance stats on each update"""
		if pf: self.statistics['pagefaults'] += 1
		if diskwrite: self.statistics['diskwrites'] += 1
		self.statistics['accesses'] += 1


	def update(self, page):
		# see if page is in memory
		#index = self.find_page(page)
		try:
			index = self.index_cache[page.page_number()]
		except KeyError:
			index = -1

		pf = True
		diskwrite = False
		# Memory hit - page is in memory
		if index >= 0:
			# set reference bit
			self.memory[index].set_ref_bit(1)
			if page.dirty:
				# set dirty bit
				self.memory[index].set_dirty_bit()
			# not a page fault
			pf = False
		# Page fault w/ no eviction
		elif self.space_available:
			# add page reference to memory
			self.memory.append(page)
			self.update_index_cache(None, page, len(self.memory) - 1)
		# Page fault with eviction
		else:
			# find next page to evict
			old = self.evict_and_replace(page)
			if old.dirty:
				diskwrite = True


		# update statistics 
		self.update_statistics(pf, diskwrite)


		return pf

	def find_page(self, p):
		"""Search physical memory for page. Returns index if found, -1 otherwise"""
		for i, page in enumerate(self.memory):
			if page.page_number() == p.page_number():
				return i
		return -1

	def __str__(self):
		""" Formats the stats for debugging"""
		stats_str = (
			"Algorithm: Second Chance\n"
			"Number of frames: {}\n"
			"Page size: {} KB\n"
			"Total memory accesses: {}\n"
			"Total page faults: {}\n"
			"Total writes to disk: {}\n"
		).format(
			self.size,
			self.pagesize,
			self.statistics['accesses'],
			self.statistics['pagefaults'],
			self.statistics['diskwrites']
		)
		return stats_str


class VMSim(object):
	def __init__(self, trace, frames, pagesize, split):
		self.mem_trace = trace
		# Config variables
		self.frames = frames
		self.pagesize = pagesize
		self.mem_split = split
		offset = int(math.log(1024 * pagesize, 2))
		
		size_split = self.calc_frame_alloc(frames, split)
		self.memory_allocations = []
		
		# Memory
		for i, num_frames in enumerate(size_split):
			self.memory_allocations.append(SecondChance(int(num_frames), pagesize, split, offset, i))

	def calc_frame_alloc(self, frames, ratio_str):
		# need to reduce with GCF
		try:
			ratio = ratio_str.split(':')
			ratio[0], ratio[1] = int(ratio[0]), int(ratio[1])
			divisor = ratio[0] + ratio[1]
			multiplier = frames/divisor
			return (ratio[0] * multiplier, ratio[1] * multiplier)
		except (ValueError, IndexError):
			print('Incorrect memory split format')
			sys.exit()


	def run_simulation(self):

		for page_ref in self.mem_trace:
			proc_id = page_ref.process_id
			self.memory_allocations[proc_id].update(page_ref)

	def summarize_stats(self, pr_algos):
		summary = {}
		for algo in pr_algos:
			for stat in algo.statistics:
				try:
					summary[stat] += algo.statistics[stat]
				except KeyError:
					summary[stat] = algo.statistics[stat]
		return summary

	def print_stats(self):
		summary = self.summarize_stats(self.memory_allocations)
		stats_str = (
			"Algorithm: Second Chance\n"
			"Number of frames: {}\n"
			"Page size: {} KB\n"
			"Total memory accesses: {}\n"
			"Total page faults: {}\n"
			"Total writes to disk: {}"
		).format(
			self.frames,
			self.pagesize,
			summary['accesses'],
			summary['pagefaults'],
			summary['diskwrites']
		)
		print(stats_str)





def main():
	args = get_args()
	mem_trace = read_trace(args)
	vm = VMSim(mem_trace, args['numframes'], args['pagesize'], args['mem_split'])
	vm.run_simulation()
	vm.print_stats()


if __name__ == '__main__':
	main()


