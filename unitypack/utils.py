import struct
import sys
from os import SEEK_CUR
import ctypes
import datetime
import enum


def lz4_decompress(data, size):
	try:
		from lz4.block import decompress
	except ImportError:
		raise RuntimeError("python-lz4 >= 0.9 is required to read UnityFS files")

	return decompress(data, size)


def json_default(o):
    if isinstance(o, set):
        return list(o)
    return o.__dict__

def to_serializable(val):
    if isinstance(val, datetime.datetime):
        return val.isoformat() + "Z"
    elif isinstance(val, enum.Enum):
        return val.value
    elif attr.has(val.__class__):
        return attr.asdict(val)
    elif isinstance(val, Exception):
        return {
            "error": val.__class__.__name__,
            "args": val.args,
        }
    return str(val)

# Print iterations progress
# https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = '\r')
    # Print New Line on Complete
    if iteration == total:
        prefix = ' ' * len(prefix)
        bar = ' ' * length
        percent = ' ' * len(percent)
        suffix = ' ' * len(suffix)
        print('\r%s  %s  %s  %s' % (prefix, bar, percent, suffix), end = '\r')

def extract_audioclip_samples(d) -> dict:
	"""
	Extract all the sample data from an AudioClip and
	convert it from FSB5 if needed.
	"""
	ret = {}

	if not d.data:
		# eg. StreamedResource not available
		return {}

	try:
		from fsb5 import FSB5
	except ImportError as e:
		raise RuntimeError("python-fsb5 is required to extract AudioClip")

	af = FSB5(d.data)
	for i, sample in enumerate(af.samples):
		if i > 0:
			filename = "%s-%i.%s" % (d.name, i, af.get_sample_extension())
		else:
			filename = "%s.%s" % (d.name, af.get_sample_extension())
		try:
			sample = af.rebuild_sample(sample)
		except ValueError as e:
			print("WARNING: Could not extract %r (%s)" % (d, e))
			continue
		ret[filename] = sample

	return ret


class BinaryReader:
	def __init__(self, buf, endian="<"):
		self.buf = buf
		self.endian = endian

	def align(self):
		old = self.tell()
		new = (old + 3) & -4
		if new > old:
			self.seek(new - old, SEEK_CUR)

	def read(self, *args):
		return self.buf.read(*args)

	def seek(self, *args):
		return self.buf.seek(*args)

	def tell(self):
		return self.buf.tell()

	def read_string(self, size=None, encoding="utf-8"):
		if size is None:
			ret = self.read_cstring()
		else:
			ret = struct.unpack(self.endian + "%is" % (size), self.read(size))[0]
		try:
			return ret.decode(encoding)
		except UnicodeDecodeError:
			return ret

	def read_cstring(self) -> bytes:
		ret = []
		c = b""
		while c != b"\0":
			ret.append(c)
			c = self.read(1)
			if not c:
				raise ValueError("Unterminated string: %r" % (ret))
		return b"".join(ret)

	def read_boolean(self) -> bool:
		return bool(struct.unpack(self.endian + "b", self.read(1))[0])

	def read_byte(self) -> int:
		return ctypes.c_byte( struct.unpack(self.endian + "b", self.read(1))[0] ).value

	def read_ubyte(self) -> int:
		return ctypes.c_ubyte( struct.unpack(self.endian + "B", self.read(1))[0] ).value

	def read_int16(self) -> int:
		return ctypes.c_int16( struct.unpack(self.endian + "h", self.read(2))[0] ).value

	def read_uint16(self) -> int:
		return ctypes.c_uint16( struct.unpack(self.endian + "H", self.read(2))[0] ).value

	def read_int(self) -> int:
		return ctypes.c_int( struct.unpack(self.endian + "i", self.read(4))[0] ).value

	def read_uint(self) -> int:
		return ctypes.c_uint( struct.unpack(self.endian + "I", self.read(4))[0] ).value

	def read_float(self) -> float:
		return struct.unpack(self.endian + "f", self.read(4))[0]

	def read_int64(self) -> int:
		return ctypes.c_int64( struct.unpack(self.endian + "q", self.read(8))[0] ).value

	def read_uint64(self) -> int:
		return ctypes.c_uint64( struct.unpack(self.endian + "Q", self.read(8))[0] ).value
