# from collections import namedtuple
import time
import os
import xml.etree.ElementTree as ET

SOURCE_FILE_NAME = 'morteza.pdf'
# SOURCE_FILE_NAME = 'rev.pdf'
PAGE_TAG = 'page'
FONT_TAG = 'fontspec'
TEXT_TAG = 'text'
LINK_TAG = 'a'
OUTLINE_TAG = 'outline'
ITEM_TAG = 'item'
SIZE_ATTR = 'size'
PAGE_ATTR = 'page'
ID_ATTR = 'id'
FONT_ATTR = 'font'
NUMBER_ATTR = 'number'

original_dict_type = dict
original_list_type = list

IGNORE_LIST = ['the', 'and', 'to', 'of', 'a', 'in', 'is', 'for', 'are' 'as', 'that', 'with', 'without', 'can', 'on',
	'from', 'be', 'it', 'this', 'by', 'an', 'has', 'not', 'at', 'its', 'their', 'we', 'about', 'all', 'such', 'these',
	'many', 'have', 'what', 'also', 'so', 'into', 'how', 'they', 'over', 'under', 'are', 'as', 'more', 'or', 'which',
	'was']


class MyList(list):
	def sorted(self, cmp=None, key=None, reverse=False):
		""" Sort the list in place, using list().sort(), and return itself """
		self.sort(cmp, key, reverse)
		return self
	
	def appended(self, x):
		""" Append x to the list list().append(), and return itself """
		self.append(x)
		return self


list = MyList


class MyDict(dict):
	def keys(self):
		return MyList(original_dict_type.keys(self))


dict = MyDict


class ElType(object):
	text = 'text'
	sub = 'sub'
	title = 'head'
	link = 'link'
	italic = 'italic'
	bold = 'bold'


class ElementObjectAbstract(object):
	""" stores an xml tag object from ElementTree """
	def __init__(self, el):
		assert isinstance(el, ET.Element)
		self._element = el
	
	def get(self, key, default=None):
		return self._element.get(key, default)
	
	@property
	def el(self):
		return self._element


class FontObject(ElementObjectAbstract):
	""" represents an xml font tag extracted from a PDF by pdftohtml linux software """
	rank = 0
	rel_rank = 0
	type = ''
	
	def __init__(self, el):
		super(FontObject, self).__init__(el)
		self.id = int(el.get(ID_ATTR))
		self.size = el.get(SIZE_ATTR)
	
	@property
	def type_rank(self):
		return '%s%s' % (self.type, abs(self.rel_rank) or '')
	
	def __repr__(self):
		return '<#%s %s s:%s>' % (self.id, self.type_rank, self.size)


class TextObject(ElementObjectAbstract):
	""" represents an xml text tag extracted from a PDF by pdftohtml linux software """
	text = ''
	rank = 0
	_type_rank = ''
	_carry_over = False
	_word_list = None
	
	def __init__(self, el, font=None, page=0, line=0, next_line=None):
		"""
		
		:param el:
		:type el: ET.element
		:param font:
		:type font: FontObject | NoneType
		"""
		super(TextObject, self).__init__(el)
		self.font_id = int(el.get(FONT_ATTR))
		for each in self.el.itertext():
			self.text += each
		self.font = font
		self.page = page
		self.line = line
		self.next_line = next_line
		self._word_list = list()
		if self.font:
			self.rank = abs(self.font.rel_rank)
			self.type = self.font.type
			self._type_rank = self.font.type_rank
	
	@property
	def type_rank(self):
		if not self._type_rank and self.font:
			self._type_rank = self.font.type_rank
		return self._type_rank
	
	@property
	def short_type(self):
		rank = '' if not self.rank else str(self.rank)
		return '%s%s' % (self.type[0], rank)
	
	@property
	def word_list(self):
		if not self._word_list:
			for each_one in self.text.strip().split(' '):
				for each in each_one.split('\t'):
					if each:
						self._word_list.append(each)
		return self._word_list
	
	def word_count(self):
		""" Get a WordList of this line of text, saves page, line and position of each word instance
		
		:return: a WordList of this line of text, saves page, line and position of each word instance
		:rtype: WordList
		"""
		pos = 0
		word_l = WordList()
		
		exclude = False
		
		for sub in self.el.iterfind('a'):
			href = sub.attrib['href'].strip()
			# text = sub.text.strip() if sub.text else ''
			if href.startswith('.html#'):
				# Internal Anchor
				# print 'A#%s : %s' % (href.replace('.html#', ''), text)
				pass
			elif href.startswith('mailto:'):
				# Mail address
				exclude = True
				# print 'M %s : %s' % (text, href.replace('mailto:', ''))
			else:
				# Regular link
				exclude = True
				# print "L %s : %s" % (href, text)
		
		if not exclude:
			for each in self.word_list:
				if not self._carry_over:
					# aggregate line-split words
					if each.endswith('-') and self.next_line:
						self.next_line._carry_over = True
						assert isinstance(self.next_line, TextObject)
						each = each[:-1] + self.next_line.word_list[0]
					word_l.add(WordInstance(each, self.page, self.line, pos))
				else:
					self._carry_over = False
				pos += 1
		return word_l
	
	def __repr__(self):
		return '<%s l:%s>' % (self.type_rank, len(self.text))


class WordInstance(object):
	""" serves as a word storage object
	saves the word position (page, line, word no (aka position)
	also clean the word of all symbols like punctuation and alike (see WordInstance.clear_list and
	WordInstance.strip_list)
	
	WordInstance().id is the cleaned version of the word, used for indexing while WordInstance().textual is its
	acutal representation in context
	"""
	def __init__(self, word='', page=0, line=0, position=0):
		self._word = self.word_clean(word)
		self._id = self._word.lower()
		self.page = page
		self.line = line
		self.position = position
	
	@staticmethod
	def remove_item_list_from_word(word, a_list=list(), strip_list=list()):
		assert isinstance(word, basestring)
		for each_item in a_list:
			word = word.replace(each_item, '')
		for each_item in strip_list:
			if word.endswith(each_item):
				word = word[:-1]
			if word.startswith(each_item):
				word = word[1:]
		return word
	
	clear_list = ['.', ',', '(', ')', ':', '?', '!', ';', '+', '=', '"', unichr(8220), unichr(8221),
		unichr(8230), unichr(8226), unichr(65533), unichr(169), unichr(8211)]
	strip_list = [unichr(8216), unichr(8217), "'"]
	
	def word_clean(self, word):
		assert isinstance(word, basestring)
		return unicode(self.remove_item_list_from_word(word.strip(), self.clear_list, self.strip_list))
	
	@property
	def textual(self):
		return self._word.encode('utf-8')
	
	@property
	def id(self):
		return self._id.encode('utf-8')
	
	def __str__(self):
		return self.textual
		
	def __repr__(self):
		return str('<W:%s>' % self.id)


class CustomDict(dict):
	def sum(self, key, new_value):
		if key in self.keys():
			new_value += self[key]
		self[key] = new_value
	
	def __add__(self, other):
		import copy
		if not isinstance(other, CustomDict):
			print type(other)
		assert isinstance(other, CustomDict)
		new_l = copy.copy(self)
		for key, value in other.iteritems():
			new_l.sum(key, value)
		return new_l
	
	def add(self, key, data=None):
		if data:
			self.sum(key, data)
		else:
			self.sum(key, list())
		return True
			
	def count(self, key=None):
		return len(self.get(key, list())) if key else len(self.keys())
		
		
class EntryStorage(object):
	def __init__(self, enforce_type=None):
		self.enforce_type = enforce_type
		self.entries = CustomDict()
		self.count = 0
		self._inst_list_text = ''
	
	def __getitem__(self, item):
		return self.entries[item]
	
	def __setitem__(self, key, value):
		self.entries[key] = value
	
	def __add__(self, other):
		import copy
		assert not self.enforce_type or isinstance(other, self.enforce_type)
		new_l = copy.copy(self)
		new_l.entries += copy.copy(other.entries)
		new_l.count += other.count
		return new_l
	
	def get(self, key, default=None):
		return self.entries.get(key, default)
	
	
class WordEntry(EntryStorage):
	def __init__(self, word_obj=None):
		super(WordEntry, self).__init__(self.__class__)
		self.id = ''
		self.rank = 0
		if word_obj:
			self.add(word_obj)
		
	def add(self, word_obj):
		assert isinstance(word_obj, WordInstance)
		if self.count == 0: # empty dict, not initialized
			self.id = word_obj.id
		assert self.id == word_obj.id
		
		self._add_word(word_obj)
		
	def _add_word(self, word_obj):
		if self.entries.add(word_obj.textual, [word_obj]):
			self.count += 1
	
	@property
	def instances_list_str(self):
		if not self._inst_list_text:
			_ = self.entries_list_str
		return self._inst_list_text
	
	@property # WARNING : NON GENERIC
	def entries_list_str(self):
		text_cache = ''
		word_list = ''
		for text, inst_list in self.entries.iteritems():
			text_cache += '%s*%s, ' % (len(inst_list), text)
			if not self._inst_list_text:
				for word_instance in inst_list:
					word_list += 'p%sl%s:%s %s\n' % (word_instance.page, word_instance.line, word_instance.position, text)
		self._inst_list_text = word_list
		return text_cache[:-2]
	
	def tell(self):
		return '%s*%s : %s\n%s' % (self.count, self.id, self.entries_list_str, self.instances_list_str)
	
	def get_by_page(self, page):
		new_entry = WordEntry()
		for key, value in self.entries.iteritems():
			if key.page == page:
				new_entry.add(key)
		return new_entry

	def __str__(self):
		return '%s*%s : %s' % (self.count, self.id, self.entries_list_str)
	
	def __repr__(self):
		return '<WE %s:%s>' % (self.id, self.count)
		

class WordList(EntryStorage):
	def __init__(self, a_dict=None):
		super(WordList, self).__init__(None)
		if a_dict:
			self.entries = a_dict
		
	def add(self, word):
		assert isinstance(word, WordInstance)
		if word.id:
			entry = self.get(word.id, WordEntry())
			entry.add(word)
			# if word.id in self.entries:
			self[word.id] = entry
	
	def show(self):
		for word in self.entries.keys().sorted():
			print 'WL: %s' % str(self.entries.get(word))
	
	def top_words(self, max_items=0, ignore_list=True, min_count=1, max_count=0):
		tmp_list = list()
		tmp_dict = dict()
		for word_id, word_entry in self.entries.iteritems():
			if not ignore_list or word_id not in IGNORE_LIST:
				key = word_entry.count
				if key >= min_count and (not max_count or key <= max_count):
					tmp_dict[key] = tmp_dict.get(key, list()).appended(word_entry)
		
		i = 1
		for count in tmp_dict.keys().sorted(reverse=True):
			# tmp_list.append("#%s: %s" % (i, tmp_dict[count]))
			tmp_list.append(tmp_dict[count])
			i += 1
			if max_items and i > max_items:
				break
		
		the_len = len(tmp_dict.keys())
		max_items = the_len if not max_items or max_items < the_len else max_items
		return tmp_list[0:max_items]
	
	def top_words_str(self, max_items=0, ignore_list=True, min_count=1, max_count=0):
		i = 1
		text_temp = ''
		for each in self.top_words(max_items, ignore_list, min_count, max_count):
			text_temp += "#%s: %s\n" % (i, each)
			i += 1
		
		return text_temp
	
	@property
	def instances_count(self):
		count = 0
		for inst_list in self.entries.itervalues():
			count += inst_list.count()
		return count
	
	def __repr__(self):
		return '<Wl:%s>' % len(self.entries)
			

class OutlineItem(ElementObjectAbstract):
	def __init__(self, el, item_id=0):
		super(OutlineItem, self).__init__(el)
		self.page_in = int(el.get(PAGE_ATTR))
		self.page_out = 0
		self.id = item_id
		self.text = el.text
		
	@property
	def page_range(self):
		if self.page_in != self.page_out:
			return 'p(%s:%s)' % (self.page_in, self.page_out)
		else:
			return 'p%s' % self.page_in
	
	def __repr__(self):
		return '<#%s %s "%s">' % (self.id, self.page_range, self.text)


class Struct:
	def __init__(self, **entries):
		self.__dict__.update(entries)
		
	def __repr__(self):
		return str(self.__dict__)


class PDFtoText(object):
	PDF_FILE_NAME = SOURCE_FILE_NAME
	SUB_FOLDER = SOURCE_FILE_NAME + '.xml_out'
	# XML_FILE_NAME = PDF_FILE_NAME + '.xml'
	XML_FILE_NAME = 'data.xml'
	_hash = None
	
	def __init__(self, source_file_name):
		if os.path.exists(source_file_name):
			self.PDF_FILE_NAME = source_file_name
		else:
			raise 'PDF file not found : %s' % source_file_name
		# if os.path.exists(self.xml_destination):
		# 	os.remove(self.xml_destination)
		self._xml_object = None
		
		self._all_fonts = list()
		self._font_hierachy_rank = list()
		self._font_hierachy_by_id = dict()
		self._font_id_count_dict = dict()
		self._font_size_count_dict = dict()
		self._outline = list()
		self.run()
	
	@staticmethod
	def run_cmd(cmd, show=True):
		if show:
			print '$', cmd, ':'
		os.system(cmd)
		
	@property
	def pdf_destination(self):
		return self.SUB_FOLDER + '/' + self.PDF_FILE_NAME
		
	@property
	def xml_destination(self):
		return self.SUB_FOLDER + '/' + self.XML_FILE_NAME
	
	@property
	def xml_created(self):
		return os.path.exists(self.xml_destination)
	
	def produce_xml(self):
		# run_cmd('cd %s' % SUB_FOLDER)
		self.run_cmd('pdftohtml -xml %s %s' % (self.pdf_destination, self.xml_destination))
		
	def copy2sub(self):
		import shutil
		try:
			if os.path.exists(self.SUB_FOLDER):
				shutil.rmtree(self.SUB_FOLDER)
			os.mkdir(self.SUB_FOLDER)
			shutil.copy(self.PDF_FILE_NAME, self.SUB_FOLDER)
		except Exception as e:
			print e
			return False
		return True
	
	def md5(self, message):
		import hashlib
		m = hashlib.md5()
		m.update(message)
		return m.hexdigest()
	
	def run(self):
		if not self._hash:
			self._hash = self.md5(open(self.PDF_FILE_NAME, 'rb').read())
			self.SUB_FOLDER = self._hash
		if not self.xml_created and self.copy2sub():
			start = time.clock()
			if not self.xml_created:
				self.produce_xml()
			elapsed = time.clock()
			elapsed = elapsed - start
			# print 'DONE in %s sec' % duration
			if self.xml_created:
				print 'DONE in %0.2f sec' % (elapsed * 10000)
			else:
				print 'failure'
	
	@property
	def xml_object(self):
		"""
		:return:
		:rtype: ET.Element
		"""
		self.run()
		if self._xml_object is None:
			self._xml_object = ET.parse(self.xml_destination).getroot()
		return self._xml_object

	@staticmethod
	def find_in_tree(tree, node):
		found = tree.find(node)
		if found is not None:
			print "No %s in file" % node
			found = []
		return found
	
	def find(self, node):
		return self.find_in_tree(self.xml_object, node)
	
	@staticmethod
	def get_max_value_entry(a_dict):
		the_max = 0
		max_obj = None
		for k, v in a_dict.iteritems():
			if v > the_max:
				the_max = v
				max_obj = k
		return max_obj, a_dict.get(max_obj, None)
	
	def extract_font_by_id_primitive(self, font_id):
		return FontObject(self.xml_object.find('%s/%s[@%s="%s"]' % (PAGE_TAG, FONT_TAG, ID_ATTR, font_id)))
	
	@property
	def all_fonts(self):
		if not self._all_fonts:
			font_dict = dict()
			for each in self.xml_object.findall('%s/%s' % (PAGE_TAG, FONT_TAG)):
				assert isinstance(each, ET.Element)
				font_id = int(each.get(ID_ATTR))
				font_dict[font_id] = FontObject(each)
			self._all_fonts = font_dict
			_ = self.font_hierachy_ids
		return self._all_fonts
	
	@property
	def font_hierachy_ids(self):
		hierachy = list()
		hierachy_dict = dict()
		
		if not self._all_fonts:
			_ = self.all_fonts
		
		if not self._font_hierachy_rank:
			font_h = dict()
			# create a dir with all fonts id grouped in list by size
			for k, v in self._all_fonts.iteritems():
				size = int(v.get(SIZE_ATTR))
				tmp_list = font_h.get(size, list())
				tmp_list.append(v)
				
				font_h[size] = tmp_list
			# sorting the keys to order them
			k_list = font_h.keys()
			k_list.sort()
			# create a hierachy list where each group is ordered by size rank
			for each_size in k_list:
				a_list = font_h.get(each_size, list())
				b_list = list()
				for each in a_list:
					b_list.append(each.id)
				hierachy.append(b_list)
			self._font_hierachy_rank = hierachy
			# create a dict to associate each font_id with it's rank
			i = 0
			for each_group in hierachy:
				for each_id in each_group:
					hierachy_dict.update({each_id: i})
				i += 1
			# the rank of text items
			text_rank = hierachy_dict[self.text_font_el.id]
			# go through all fonts dict to attribute then their rank, type and relative rank to text
			for k, v in hierachy_dict.iteritems():
				if k in self._all_fonts.keys():
					self._all_fonts[k].rank = v
					self._all_fonts[k].rel_rank = v - text_rank
					if v == text_rank:
						self._all_fonts[k].type = ElType.text
					elif v > text_rank:
						self._all_fonts[k].type = ElType.title
					else:
						self._all_fonts[k].type = ElType.sub
						
			self._font_hierachy_by_id = hierachy_dict
		return self._font_hierachy_by_id
			
	@property
	def font_id_count(self):
		if not self._font_id_count_dict:
			size_dict = dict()
			id_dict = dict()
			
			for each in self.xml_object.iter(PAGE_TAG):
				assert isinstance(each, ET.Element)
				for each2 in each.findall(TEXT_TAG):
					assert isinstance(each2, ET.Element)
					font_id = each2.get(FONT_ATTR)
					font = self.extract_font_by_id_primitive(font_id)
					size = int(font.get(SIZE_ATTR))
					size_dict.update({size: size_dict.get(size, 0) + 1})
					id_dict.update({font_id: id_dict.get(font_id, 0) + 1})
			self._font_id_count_dict = id_dict
			self._font_size_count_dict = size_dict
		return self._font_id_count_dict
	
	@property
	def font_size_count(self):
		if not self._font_size_count_dict:
			_ = self.font_id_count
		return self._font_size_count_dict
	
	@property
	def text_font_el(self):
		# max_size = self.get_max_value_entry(self.font_size_count)[0]
		max_id = self.get_max_value_entry(self.font_id_count)[0]
		return self.extract_font_by_id_primitive(max_id)
	
	def get_text_list(self, start=1, stop=0):
		page_cache = dict()
		for each_page in self.xml_object.iter(PAGE_TAG):
			page_num = int(each_page.get(NUMBER_ATTR))
			if page_num >= start:
				if stop and page_num > stop:
					break
				
				# text_list.append('PAGE %s:' % page_num)
				line = 0
				text_list = list()
				for each_text in each_page.iter(TEXT_TAG):
					font = self.all_fonts.get(int(each_text.get(FONT_ATTR)))
					text = TextObject(each_text, font, page_num, line)
					if line > 0:
						text_list[len(text_list) - 1].next_line = text
					text_list.append(text)
					line += 1
				print '.',
				page_cache.update({page_num: text_list})
		return page_cache
	
	def get_text_str(self, start=1, stop=0):
		page_dict = self.get_text_list(start, stop)
		print ''
		text_cache = ''
		for page_num, text_list in page_dict.iteritems():
			text_cache += 'PAGE %s:\n' % page_num
			for each in text_list:
				if isinstance(each, TextObject):
					text_cache += '%s: %s\n' % (each.short_type, each.text)
			print '.',
		return text_cache[:-1]
	
	def text_count(self, start=1, stop=0):
		page_dict = self.get_text_list(start, stop)
		print ''
		word_count = Struct()
		word_count.page = dict()
		word_count.all = WordList()
		
		for page_num, text_list in page_dict.iteritems():
			local_word_count = WordList()
			i = 0
			for each_line in text_list:
				if isinstance(each_line, TextObject):
					local_word_count += each_line.word_count()
				i += 1
			word_count.page.update({page_num: local_word_count})
			word_count.all += local_word_count
			print '.',
		return word_count
	
	def full_dump(self):
		print 'OUTLINE:\n%s\n\n%s' % (self.outline_str,  self.get_text_str())
	
	@property
	def last_page_el(self):
		"""
		
		:return:
		:rtype: ET.Element
		"""
		return self.xml_object.findall(PAGE_TAG)[-1]
	
	@property
	def outline(self):
		if not self._outline:
			i = 0
			outline_dict = dict()
			for each_item in self.xml_object.iterfind('%s/%s' % (OUTLINE_TAG, ITEM_TAG)):
				outline = OutlineItem(each_item, i)
				outline_dict.update({outline.page_in: outline})
				# self._outline.append()
				i += 1
			# sort this list if ever the index is out of order
			for each in outline_dict.keys().sorted():
				self._outline.append(outline_dict.get(each))
			# run through the list to get the ending page of each chapter by looking for the starting page of the
			# next chapter, or the last page of the doc
			i = 0
			max_i = len(self._outline) - 1
			for each in self._outline:
				assert isinstance(each, OutlineItem)
				if i < max_i: # there is a next element
					each.page_out = self._outline[i+1].page_in - 1
				else:
					each.page_out = self.last_page_el.get(NUMBER_ATTR)
				i += 1
		return self._outline
	
	@property
	def outline_str(self):
		text_cache = ''
		for each in self.outline:
			text_cache += ('%s :' % each.page_range).ljust(12) + ' %s\n' % each.text
		return text_cache[:-1]
		
	
def test():
	x_obj = PDFtoText(SOURCE_FILE_NAME)
	font = x_obj.text_font_el
	print 'text items are most likely with font id:', font.id, 'size:', font.size
	return x_obj
