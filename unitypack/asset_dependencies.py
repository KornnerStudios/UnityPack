from enum import IntEnum
from .asset import Asset
from .assetbundle import AssetBundle
from .engine.preload_data import PreloadData
from .engine.asset_bundle import AssetBundle as AssetBundleData, AssetInfo
from .utils import json_default, printProgressBar
import json
import logging

# forward declarations
class AssetDependencyDatabase:
	pass
class AssetDependencyTable:
	pass


class AssetDependencyPPtr:
	def __init__(self, obj_ptr):
		if obj_ptr is None:
			self.file_id = -1
			self.path_id = -1
		else:
			self.file_id = obj_ptr.file_id
			self.path_id = obj_ptr.path_id

	def __repr__(self):
		return "(file_id=%r, path_id=%r)" % (
			self.file_id, self.path_id
		)

	@property
	def is_null(self):
		return self.file_id == -1 and self.path_id == -1

	@property
	def is_not_null(self):
		return self.file_id != -1 and self.path_id != -1

	def __bool__(self):
		return self.is_not_null

	@property
	def is_local_object(self):
		return self.file_id == 0 and self.path_id != -1

class AssetDependencyPreloadData:
	def __init__(self):
		self.dependencies = []
		self.assets = []

	def setup(self, preload_data: PreloadData):
		for dep in preload_data.m_Dependencies:
			self.dependencies.append(dep)

		for obj_ptr in preload_data.m_Assets:
			self.assets.append(AssetDependencyPPtr(obj_ptr))

	def cleanup_setup_data(self):
		if len(self.dependencies) == 0:
			self.dependencies = None

		# don't need this since it's processed when building reports
		del self.preload_table

	def build_report(self, db: AssetDependencyDatabase, owner_table: AssetDependencyTable):
		for asset in self.assets:
			db.report.add_object_reference(db, owner_table, asset)

class AssetDependencyAssetInfo:
	def __init__(self, path, asset_info):
		self.source_path = path
		self.preload_index = asset_info.preloadIndex
		self.preload_size = asset_info.preloadSize
		self.object_ptr = None
		asset = asset_info.asset
		if asset is not None:
			self.object_ptr = AssetDependencyPPtr(asset)

class AssetDependencyAssetBundlePreloadInfo:
	def __init__(self, info: AssetInfo):
		self.preload_index = info.preloadIndex
		self.preload_size = info.preloadSize
		self.object_ptr = AssetDependencyPPtr(info.asset)

class AssetDependencyAssetBundleData:
	def __init__(self):
		self.name = None
		self.dependencies = []
		self.preload_table = []
		self.exports = []
		self.export_names_by_path_id = {}
		self.main_asset = None

	def setup(self, bundle_data: AssetBundleData):
		self.name = bundle_data.m_AssetBundleName

		for dep in bundle_data.m_Dependencies:
			self.dependencies.append(str(dep))

		for preload_asset in bundle_data.m_PreloadTable:
			preload_ptr = AssetDependencyPPtr(preload_asset)
			self.preload_table.append(preload_ptr)

		for path, asset_info in bundle_data.m_Container.items():
			info = AssetDependencyAssetInfo(path, asset_info)
			self.exports.append(info)
			if info.object_ptr is not None and info.object_ptr.path_id != -1:
				self.export_names_by_path_id[info.object_ptr.path_id] = path

		if bundle_data.m_MainAsset is not None:
			self.main_asset = AssetDependencyAssetBundlePreloadInfo(bundle_data.m_MainAsset)

	def cleanup_setup_data(self):
		if len(self.dependencies) == 0:
			self.dependencies = None

		# don't need this since it's processed when building reports
		del self.preload_table
		# don't need this, it's just duplicate data
		del self.export_names_by_path_id

		if self.main_asset is not None:
			if self.main_asset.preload_size == 0 and self.main_asset.object_ptr.is_null:
				self.main_asset = None

	def build_report(self, db: AssetDependencyDatabase, owner_table: AssetDependencyTable):
		for asset in self.preload_table:
			db.report.add_object_reference(db, owner_table, asset)

class AssetDependencyObject:
	def __init__(self):
		self.path_id = -1
		self.unity_type = None
		self.size = -1
		self.name = None
		self.referenced_by = None

	def set_name(self, obj, asset_bundle_data: AssetDependencyAssetBundleData):
		# try to avoid obj.read's, which will cause chunks to get compressed as needed
		if asset_bundle_data is not None:
			if self.path_id in asset_bundle_data.export_names_by_path_id:
				self.name = asset_bundle_data.export_names_by_path_id[self.path_id]
				return

		name = obj.read_name_only()
		if name is not None:
			self.name = name['m_Name']

		if self.name == "":
			self.name = None

	def add_reference(self, db: AssetDependencyDatabase, src_table: AssetDependencyTable):
		if self.referenced_by is None:
			self.referenced_by = set()

		self.referenced_by.add(src_table.name)

class AssetDependencyTable:
	def __init__(self):
		self.table_index = -1
		self.source_file = None
		self.name = None
		self.preload_data = None
		self.asset_bundle_data = None
		self.external_refs = []
		self.objects = {}

	def setup(self, asset: Asset):
		self.name = asset.name

		# fix standalone .asset or level files where the asset.name returns the file path
		last_slash = self.name.rfind('\\')
		if last_slash >= 0:
			self.name = self.name[last_slash+1:]

		for ref in asset.external_refs:
			if ref == asset:
				continue
			self.external_refs.append(ref.file_path)

		# find and gather start up info first
		for id, obj in asset.objects.items():
			if obj.type_tree is None:
				continue

			if obj.type == "PreloadData":
				d = obj.read()
				self.preload_data = AssetDependencyPreloadData()
				self.preload_data.setup(d)
			elif obj.type == "AssetBundle":
				d = obj.read()
				self.asset_bundle_data = AssetDependencyAssetBundleData()
				self.asset_bundle_data.setup(d)

		l = len(asset.objects)
		index = 0
		printProgressBar(index, l, prefix = 'Progress:', suffix = 'Complete', length = 50)

		for id, obj in asset.objects.items():
			index += 1
			printProgressBar(index, l, prefix = 'Progress:', suffix = 'Complete', length = 50)

			if obj.type_tree is None:
				continue

			if obj.type == "PreloadData":
				continue
			elif obj.type == "AssetBundle":
				continue
			else:
				dobj = AssetDependencyObject()
				dobj.path_id = obj.path_id
				dobj.unity_type = str(obj.type)
				dobj.size = obj.size
				dobj.set_name(obj, self.asset_bundle_data)

			self.objects[dobj.path_id] = dobj

	def build_report(self, db: AssetDependencyDatabase):
		if self.preload_data is not None:
			self.preload_data.build_report(db, self)

		if self.asset_bundle_data is not None:
			self.asset_bundle_data.build_report(db, self)

	def cleanup_setup_data(self):
		if self.preload_data is not None:
			self.preload_data.cleanup_setup_data()

		if self.asset_bundle_data is not None:
			self.asset_bundle_data.cleanup_setup_data()

		# cull objects which don't have any references
		ks = [k for k,v in self.objects.items() if v.referenced_by==None]
		for k in ks:
			self.objects.pop(k)

	def get_external_ref_name(self, file_id: int) -> str:
		if file_id == 0:
			return name.lower()

		for index, ref_path in enumerate(self.external_refs):
			if (index+1) == file_id:
				return AssetDependencyDatabase.external_ref_path_to_name(ref_path)

		return None


class AssetDependencyReport:
	def __init__(self):
		pass

	def add_object_reference(self, db: AssetDependencyDatabase, src_table: AssetDependencyTable, obj_ptr: AssetDependencyPPtr):
		if obj_ptr.is_null:
			return
		# skip local files
		if obj_ptr.file_id == 0:
			return

		external_ref_name = src_table.get_external_ref_name(obj_ptr.file_id)
		external_ref_table_index = db.external_ref_name_to_table_index[external_ref_name]
		external_ref_table = db.dependency_table[external_ref_table_index]

		if obj_ptr.path_id not in external_ref_table.objects:
			#raise Exception("{0} in {1} not in {2}".format(obj_ptr, src_table.name, external_ref_name))
			logging.warning("{0} in {1} not in {2}".format(obj_ptr, src_table.name, external_ref_name))
			return

		external_obj = external_ref_table.objects[obj_ptr.path_id]
		external_obj.add_reference(db, src_table)


class AssetDependencyDatabase:
	def __init__(self):
		self.dependency_table = []
		self.external_ref_name_to_table_index = {}
		self.report = AssetDependencyReport()

	def build_from_bundle(self, source_file: str, bundle: AssetBundle):
		for asset in bundle.assets:
			self.add_asset(source_file, asset)

	def add_asset(self, source_file: str, asset: Asset):
		table = AssetDependencyTable()
		table.source_file = source_file
		table.setup(asset)

		# NOTE variant bundles all have the same name (CAB-...), so skip everything but the first encountered variant
		if table.name.lower() in self.external_ref_name_to_table_index:
			return
		
		table.table_index = len(self.dependency_table)
		self.dependency_table.append(table)
		self.external_ref_name_to_table_index[table.name.lower()] = table.table_index

	def write_to_json_file(self, json_path: str):
		for table in self.dependency_table:
			table.build_report(self)

		for table in self.dependency_table:
			table.cleanup_setup_data()

		with open(json_path, "w") as json_file:
			json_file.write(json.dumps(self, indent=4, default=json_default))

	@classmethod
	def external_ref_path_to_name(cls, ref_path: str) -> str:
		last_forward_slash = ref_path.rfind('/')
		if last_forward_slash < 0:
			return ref_path

		return ref_path[last_forward_slash+1:]
