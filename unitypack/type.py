from enum import IntEnum
from io import BytesIO
from .enums import BuildTargetPlatform
from .resources import get_resource, STRINGS_DAT
from .utils import BinaryReader

class TypeTreeHint(IntEnum):
	NULL = 0
	Bool = 1
	Char = 2
	SInt8 = 3
	UInt8 = 4
	SInt16 = 5
	UInt16 = 6
	SInt32 = 7
	UInt32 = 8
	SInt64 = 9
	UInt64 = 10
	Float = 11
	String = 12
	Other = 13


class TypeTree:
	NULL = "(null)"

	def __init__(self, format):
		self.children = []
		self.version = 0
		self.is_array = False
		self.size = 0
		self.index = 0
		self.flags = 0
		self.type = self.NULL
		self.type_hint = TypeTreeHint.NULL
		self.name = self.NULL
		self.format = format

	def __repr__(self):
		return "<%s %s (size=%r, index=%r, is_array=%r, flags=%r)>" % (
			self.type, self.name, self.size, self.index, self.is_array, self.flags
		)

	@property
	def post_align(self):
		return bool(self.flags & 0x4000)

	def load(self, buf):
		if self.format == 10 or self.format >= 12:
			self.load_blob(buf)
		else:
			self.load_old(buf)

	def load_old(self, buf):
		self.type = buf.read_string()
		self.name = buf.read_string()
		self.size = buf.read_int()
		self.index = buf.read_int()
		self.is_array = bool(buf.read_int())
		self.version = buf.read_int()
		self.flags = buf.read_int()

		num_fields = buf.read_uint()
		for i in range(num_fields):
			tree = TypeTree(self.format)
			tree.load(buf)
			self.children.append(tree)

	def load_blob(self, buf):
		num_nodes = buf.read_uint()
		self.buffer_bytes = buf.read_uint()
		node_data = BytesIO(buf.read(24 * num_nodes))
		self.data = buf.read(self.buffer_bytes)

		parents = [self]

		buf = BinaryReader(node_data)

		for i in range(num_nodes):
			version = buf.read_int16()
			depth = buf.read_ubyte()

			if depth == 0:
				curr = self
			else:
				while len(parents) > depth:
					parents.pop()
				curr = TypeTree(self.format)
				parents[-1].children.append(curr)
				parents.append(curr)

			curr.version = version
			curr.is_array = buf.read_byte()
			curr.type = self.get_string(buf.read_int())
			curr.name = self.get_string(buf.read_int())
			curr.size = buf.read_int()
			curr.index = buf.read_uint()
			curr.flags = buf.read_int()
			curr.type_hint = self.get_type_hint_index(curr.type)

	def get_string(self, offset):
		if offset < 0:
			offset &= 0x7fffffff
			data = STRINGS_DAT
		elif offset < self.buffer_bytes:
			data = self.data
		else:
			return self.NULL
		return data[offset:].partition(b"\0")[0].decode("utf-8")

	def get_type_hint_index(self, t: str) -> TypeTreeHint:
		if t == "bool":
			return TypeTreeHint.Bool
		elif t == "char":
			return TypeTreeHint.Char
		elif t == "SInt8":
			return TypeTreeHint.SInt8
		elif t == "UInt8":
			return TypeTreeHint.UInt8
		elif t == "SInt16":
			return TypeTreeHint.SInt16
		elif t == "UInt16":
			return TypeTreeHint.UInt16
		elif t == "SInt64":
			return TypeTreeHint.SInt64
		elif t == "UInt64":
			return TypeTreeHint.UInt64
		elif t in ("UInt32", "unsigned int"):
			return TypeTreeHint.UInt32
		elif t in ("SInt32", "int"):
			return TypeTreeHint.SInt32
		elif t == "float":
			return TypeTreeHint.Float
		elif t == "string":
			return TypeTreeHint.String
		elif t == self.NULL:
			return TypeTreeHint.NULL
		else:
			return TypeTreeHint.Other


class TypeMetadata:
	default_instance = None

	@classmethod
	def default(cls, asset):
		if not cls.default_instance:
			cls.default_instance = cls(asset)
			with open(get_resource("structs.dat"), "rb") as f:
				cls.default_instance.load(BinaryReader(f), format=15)
		return cls.default_instance

	def __init__(self, asset):
		self.class_ids = []
		self.type_trees = {}
		self.hashes = {}
		self.asset = asset
		self.generator_version = ""
		self.target_platform = None

	def load(self, buf, format=None):
		if format is None:
			format = self.asset.format
		self.generator_version = buf.read_string()
		self.target_platform = BuildTargetPlatform(buf.read_uint())

		if format >= 13:
			has_type_trees = buf.read_boolean()
			num_types = buf.read_int()

			for i in range(num_types):
				class_id = buf.read_int()
				if format >= 17:
					unk0 = buf.read_byte()
					script_id = buf.read_int16()
					if class_id == 114:
						if script_id >= 0:
							# make up a fake negative class_id to work like the
							# old system.  class_id of -1 is taken to mean that
							# the MonoBehaviour base class was serialized; that
							# shouldn't happen, but it's easy to account for.
							class_id = -2 - script_id
						else:
							class_id = -1
				self.class_ids.append(class_id)
				if class_id < 0:
					hash = buf.read(0x20)
				else:
					hash = buf.read(0x10)

				self.hashes[class_id] = hash

				if has_type_trees:
					tree = TypeTree(format)
					tree.load(buf)
					self.type_trees[class_id] = tree

		else:
			num_fields = buf.read_int()
			for i in range(num_fields):
				class_id = buf.read_int()
				tree = TypeTree(format)
				tree.load(buf)
				self.type_trees[class_id] = tree
