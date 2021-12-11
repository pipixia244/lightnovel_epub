import uiautomator2 as u2
from bs4 import BeautifulSoup
import cv2
import time
import numpy as np
import sys
import pickle
import os
import traceback
import click
from utils import echo


# define constants
TOP_AREA_HEIGHT = 325
BOTTOM_AREA_HEIGHT = 200
IMAGE_EQUAL_THRESHOLD = 1
SAFE_AREA_PADDING = 20
DUMP_PATH = './dump'


echo.init_subroutine()
echo.push_subroutine('Global')
# connect to device
d = u2.connect()
# print device info
echo.clog('Device Info:', d.info)


class Image:

	filePath: str = None

	shape = None
	
	def __init__(self, filePath, shape):
		self.filePath = filePath
		self.shape = shape


class EOF:
	def __init__(self):
		pass


def rotate2landscape():
	"""
	rotate screen to landscape
	:return: None
	"""
	echo.push_subroutine(sys._getframe().f_code.co_name)
	try:
		echo.clog('Rotate screen to landscape.')
		d.set_orientation('l')
	except Exception as e:
		echo.cerr(f'Error: {repr(e)}')
		traceback.print_exc()
		echo.cexit('ROTATE TO LANDSCAPE FAILED')
	finally:
		echo.pop_subroutine()


def rotate2portrait():
	"""
	rotate screen to portrait
	:return: None
	"""
	echo.push_subroutine(sys._getframe().f_code.co_name)
	try:
		echo.clog('Rotate screen to portrait.')
		d.set_orientation('n')
	except Exception as e:
		echo.cerr(f'Error: {repr(e)}')
		traceback.print_exc()
		echo.cexit('ROTATE TO PORTRAIT FAILED')
	finally:
		echo.pop_subroutine()


def take_screenshot():
	"""
	Take a screenshot
	:return: a numpy array of the screenshot
	"""
	echo.push_subroutine(sys._getframe().f_code.co_name)
	try:
		echo.clog('Take a screenshot.')
		screenshot = d.screenshot(format='opencv')
		if (d.info['displayHeight'] - d.info['displayWidth']) * \
			(screenshot.shape[0] - screenshot.shape[1]) < 0:
			screenshot = cv2.rotate(screenshot, cv2.ROTATE_90_COUNTERCLOCKWISE)
		return screenshot
	except Exception as e:
		echo.cerr(f'Error: {repr(e)}')
		traceback.print_exc()
		echo.cexit('TAKE SCREENSHOT FAILED')
	finally:
		echo.pop_subroutine()


def get_image(x1, y1, x2, y2) -> Image:
	"""
	Get image from device screen
	:param x1: top left x of image bound
	:param y1: top left y of image bound
	:param x2: bottom right x of image bound
	:param y2: bottom right y of image bound
	:return: Image object
	"""
	echo.push_subroutine(sys._getframe().f_code.co_name)
	try:
		# click center of image
		click_x = (x1 + x2) / 2
		click_y = (y1 + y2) / 2
		if click_y > d.info['displayHeight'] - BOTTOM_AREA_HEIGHT or click_y < TOP_AREA_HEIGHT: 
			if y1 < TOP_AREA_HEIGHT:
				click_y = (y2 + TOP_AREA_HEIGHT) / 2
			elif y2 > d.info['displayHeight'] - BOTTOM_AREA_HEIGHT:
				click_y = (y1 + d.info['displayHeight'] - BOTTOM_AREA_HEIGHT) / 2
			else:
				raise Exception('Image is not in the visible area')

		click_x = click_x / d.info['displayWidth']
		click_y = click_y / d.info['displayHeight']

		time.sleep(1)
		echo.clog('Click at:', click_x, click_y)
		d.click(click_x, click_y)
		time.sleep(1)
		# take screenshot
		screenshot = take_screenshot()
		# go back
		echo.clog('Press back.')
		d.press('back')
		# get ride of navigation bar part of image
		cropped_image = screenshot[TOP_AREA_HEIGHT:, :, :]
		# calculate pixel sum of image on vertical direction
		vert = np.sum(np.sum(cropped_image, axis=2), axis=1)
		# get black border
		u = 0
		for i in vert:
			if i == 0:
				u += 1
			else:
				break
		vert = vert[::-1]
		b = 0
		for i in vert:
			if i == 0:
				b += 1
			else:
				break
		# crop black border out of image
		if b == 0:
			vert_cropped_image = cropped_image[u:, :, :]
		else:
			vert_cropped_image = cropped_image[u: -b, :, :]
		# calculate pixel sum of image on horizontal direction
		horz = np.sum(np.sum(vert_cropped_image, axis=2), axis=0)
		# get black border
		l = 0
		for i in horz:
			if i == 0:
				l += 1
			else:
				break
		horz = horz[::-1]
		r = 0
		for i in horz:
			if i == 0:
				r += 1
			else:
				break
		# crop black border out of image
		if r == 0:
			horz_cropped_image = vert_cropped_image[:, l:, :]
		else:
			horz_cropped_image = vert_cropped_image[:, l: -r, :]
		# save image
		image_name = os.path.join(DUMP_PATH, f'./{time.time_ns()}.png')
		cv2.imwrite(image_name, horz_cropped_image)
		echo.clog("Image saved,", image_name)
		# return image object
		return Image(image_name, horz_cropped_image.shape)
	except Exception as e:
		echo.cerr(f'Error: {repr(e)}')
		traceback.print_exc()
		echo.cexit('GET IMAGE FAILED')
	finally:
		echo.pop_subroutine()


def get_visible_elements(quick_mode=False):
	"""
	Get all visible elements on the screen
	:return: a list of visible elements
	"""
	echo.push_subroutine(sys._getframe().f_code.co_name)
	try:
		contents = []
		# dump hierarchy
		xml = d.dump_hierarchy()
		soup = BeautifulSoup(xml, 'lxml')
		# select contents
		contentView = soup.select('node[resource-id="android:id/content"] > node[class="android.widget.FrameLayout"] > node[class="android.widget.FrameLayout"] > node[class="android.view.View"] > node[class="android.view.View"] > node[class="android.view.View"] > node[class="android.view.View"] > node[class="android.view.View"] > node[class="android.view.View"]')[0].findAll('node', recursive=False)
		for child in contentView:
			bounds_str = child.attrs['bounds']
			bounds = bounds_str.split('][')
			x1 = int(bounds[0].split(',')[0][1:])
			y1 = int(bounds[0].split(',')[1])
			x2 = int(bounds[1].split(',')[0])
			y2 = int(bounds[1].split(',')[1][:-1])
			
			if y1 + SAFE_AREA_PADDING > d.info['displayHeight'] - BOTTOM_AREA_HEIGHT \
				or y2 - SAFE_AREA_PADDING < TOP_AREA_HEIGHT:
				continue
			if child.attrs['class'] == ['android.view.View']:
				if child.attrs['content-desc'] == '合集帖子\n更多' or \
					str(child.attrs['content-desc']).startswith('全部評論'):
					contents.append(EOF())
					break
				contents.append(child.attrs['content-desc'])
			elif child.attrs['class'] == ['android.widget.ImageView']:
				if quick_mode:
					contents.append(f'Image-Placeholder-{time.time_ns()}')
				else:
					contents.append(get_image(x1, y1, x2, y2))
		return contents
	except Exception as e:
		echo.cerr(f'Error: {repr(e)}')
		traceback.print_exc()
		echo.cexit('GET VISIBLE ELEMENTS FAILED')
	finally:
		echo.pop_subroutine()


def scroll_to_top():
	"""
	scroll the page to the top
	:return: None
	"""
	echo.push_subroutine(sys._getframe().f_code.co_name)
	try:
		last_top = None
		while True:
			d.swipe(0.5, 0.3, 0.5, 0.7, duration=0.1)
			contents = get_visible_elements(quick_mode=True)
			if contents[0] == last_top:
				break
			last_top = contents[0]
			echo.clog('Scrolling to top... last_top:', last_top)
	except Exception as e:
		echo.cerr(f'Error: {repr(e)}')
		traceback.print_exc()
		echo.cexit('SCROLL TO TOP FAILED')
	finally:
		echo.pop_subroutine()


def compare_content(content1, content2):
	"""
	Compare two contents
	:param content1: content 1
	:param content2: content 2
	:return: True if content1 == content2, False otherwise
	"""
	echo.push_subroutine(sys._getframe().f_code.co_name)
	try:
		t1 = type(content1)
		t2 = type(content2)
		if t1 == str and t2 == str:
			return content1 == content2
		if t1 != t2:
			return False
		if t1 != Image or t2 != Image:
			raise Exception('Unsupported type.')
		img1 = cv2.imread(content1.filePath)
		img2 = cv2.imread(content2.filePath)
		# judge whether shape of two images are same
		if img1.shape != img2.shape:
			return False
		# convert image to gray scale
		img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
		img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
		# calculate diff
		diff = cv2.absdiff(img1, img2)
		echo.clog('Image Diff between', content1.filePath, 'and', content2.filePath, ":", np.average(diff))
		return np.average(diff) < IMAGE_EQUAL_THRESHOLD
	except Exception as e:
		echo.cerr(f'Error: {repr(e)}')
		traceback.print_exc()
		echo.cexit('COMPARE CONTENT FAILED')
	finally:
		echo.pop_subroutine()


def get_content():
	"""
	scroll the page to the bottom and return the content of the page
	:return: the content of the page
	"""
	echo.push_subroutine(sys._getframe().f_code.co_name)
	try:
		scroll_to_top()
		time.sleep(2)
		echo.clog('Already scrolled to the top')
		contents = []
		while True:
			visible_contents = get_visible_elements()

			if contents == []:
				contents = visible_contents
			else:
				check_count = min(len(contents), len(visible_contents))
				# iterate from check_count to zero
				overlap_count = 0
				for i in range(check_count, 0, -1):
					flag = True
					for j in range(i):
						if not compare_content(contents[-(i - j)], visible_contents[j]):
							flag = False
							break
					if flag:
						overlap_count = i
						break
				if overlap_count < check_count:
					new_contents = visible_contents[overlap_count:]
					echo.clog('New contents:', new_contents)
					contents.extend(new_contents)
				else:
					echo.clog('Nothing New')
			# scroll down
			d.swipe(0.5, 0.7, 0.5, 0.3, duration=0.5)
			time.sleep(2)
			echo.clog('Scrolled down.')
			# check whether the page is at the bottom
			if type(contents[-1]) == EOF:
				echo.clog('Reached the end of the page.')
				break
		return contents[:-1]
	except Exception as e:
		echo.cerr(f'Error: {repr(e)}')
		traceback.print_exc()
		echo.cexit('GET CONTENT FAILED')
	finally:
		echo.pop_subroutine()


def dump_contents(contents):
	"""
	dump the contents to a file
	:param contents: the contents to dump
	:return: None
	"""
	echo.push_subroutine(sys._getframe().f_code.co_name)
	try:
		file_path = os.path.join(DUMP_PATH, f'./{time.time_ns()}.out')
		pickle.dump(contents, open(file_path, 'wb+'))
		echo.clog('Dumped contents to', file_path)
	except Exception as e:
		echo.cerr(f'Error: {repr(e)}')
		traceback.print_exc()
		echo.cexit('DUMP CONTENT FAILED')
	finally:
		echo.pop_subroutine()


def load_contents(file_path):
	"""
	load the contents from a file
	:param file_path: the file path
	:return: the contents
	"""
	echo.push_subroutine(sys._getframe().f_code.co_name)
	try:
		contents = pickle.load(open(file_path, 'rb'))
		echo.clog('Loaded contents from', file_path)
		return contents
	except Exception as e:
		echo.cerr(f'Error: {repr(e)}')
		traceback.print_exc()
		echo.cexit('LOAD CONTENT FAILED')
	finally:
		echo.pop_subroutine()


@click.group()
def cli():
	pass


@cli.command()
@click.option('--top-area-height', default=325, help='the height of the top area')
@click.option('--bottom-area-height', default=200, help='the height of the bottom area')
@click.option('--image-equal-threshold', default=1, help='the threshold of judging whether two images are equal')
@click.option('--safe-area-padding', default=20, help='the padding of the safe area')
@click.option('--dump-path', type=click.Path(exists=True), default='./dump', help='directory for dumping')
@click.option('--vert-dump', type=click.Path(exists=True), default=None, help='vertical content dump file path')
@click.option('--horz-dump', type=click.Path(exists=True), default=None, help='horizontal content dump file path')
def dump(top_area_height, 
		bottom_area_height, 
		image_equal_threshold, 
		safe_area_padding, 
		dump_path, 
		vert_dump, 
		horz_dump):
	"""
	dump the contents to a file
	:param top_area_height: the height of the top area
	:param bottom_area_height: the height of the bottom area
	:param image_equal_threshold: the threshold of judging whether two images are equal
	:param safe_area_padding: the padding of the safe area
	:param dump_path: directory for dumping
	:param vert_dump: vertical content dump file path
	:param horz_dump: horizontal content dump file path
	:return: dumped html file name
	"""
	echo.push_subroutine(sys._getframe().f_code.co_name)
	global TOP_AREA_HEIGHT
	global BOTTOM_AREA_HEIGHT
	global IMAGE_EQUAL_THRESHOLD
	global SAFE_AREA_PADDING
	global DUMP_PATH
	TOP_AREA_HEIGHT = top_area_height
	BOTTOM_AREA_HEIGHT = bottom_area_height
	IMAGE_EQUAL_THRESHOLD = image_equal_threshold
	SAFE_AREA_PADDING = safe_area_padding
	DUMP_PATH = dump_path

	try:
		# init directory
		if not os.path.exists(dump_path):
			os.mkdir(dump_path)

		# load and dump data
		if vert_dump is not None:
			vert_contents = load_contents(vert_dump)
			echo.clog('Loaded vertical contents from', vert_dump)
		else:
			rotate2portrait()
			echo.clog('Please make sure that the orientation is portrait **before** entering the app. If not, please quit and re-enter the page. Press <Enter> when ready ...')
			input()
			vert_contents = get_content()
			echo.clog('Got vertical contents')
			dump_contents(vert_contents)
		if horz_dump is not None:
			horz_contents = load_contents(horz_dump)
			echo.clog('Loaded horizontal contents from', horz_dump)
		else:
			rotate2landscape()			
			print('==========================')
			print('==========================')
			echo.clog('Please quit and re-enter the page. Press <Enter> when ready ...')
			input()
			horz_contents = get_content()
			echo.clog('Got horizontal contents')
			dump_contents(horz_contents)
		# recalculate typesettings
		echo.clog('Recalculating typesettings ...')

		vert_ptr = horz_ptr = 0
		new_contents = []
		vert_str = horz_str = ''
		while horz_ptr < len(horz_contents):
			this_horz = horz_contents[horz_ptr]
			if type(this_horz) == Image:
				if not horz_str.startswith(vert_str):
					raise Exception('Unexpected content')
				else:
					# string cleaned up
					if not (horz_str == '' and vert_str == ''):
						new_contents.append(horz_str)
						horz_str = vert_str = ''
					while not type(vert_contents[vert_ptr]) == Image:
						vert_ptr += 1
					# compare which image is larger
					this_vert = vert_contents[vert_ptr]
					if this_vert.shape[0] * this_vert.shape[1] > \
						this_horz.shape[0] * this_horz.shape[1]:
						new_contents.append(this_vert)
					else:
						new_contents.append(this_horz)
					horz_ptr += 1
					vert_ptr += 1
					continue
			elif type(this_horz) == str:
				horz_str += this_horz
				horz_ptr += 1

				while vert_ptr < len(vert_contents) and len(vert_str) < len(horz_str):
					this_vert = vert_contents[vert_ptr]
					if type(this_vert) != str:
						raise Exception('Unexpected content')
					vert_str += this_vert
					vert_ptr += 1
				
				if horz_str == vert_str:
					new_contents.append(horz_str)
					horz_str = vert_str = ''
					continue
			else:
				raise Exception('Unknown type:', type(this_horz))

		print(new_contents)
		dump_contents(new_contents)
			
	except Exception as e:
		echo.cerr(f'Error: {repr(e)}')
		traceback.print_exc()
		echo.cexit('DUMP CONTENT FAILED')
	finally:
		echo.pop_subroutine()


if __name__ == '__main__':
	cli()