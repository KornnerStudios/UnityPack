from .asset import Asset
from .assetbundle import AssetBundle
from .engine.preload_data import PreloadData
from .engine.asset_bundle import AssetBundle as AssetBundleData, AssetInfo
from .utils import to_serializable, printProgressBar
import json

class AssetDependencyPPtr:
	def __init__(self, obj_ptr):
		if obj_ptr is None:
			self.file_id = -1
			self.path_id = -1
		else:
			self.file_id = obj_ptr.file_id
			self.path_id = obj_ptr.path_id

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

class AssetDependencyObject:
	def __init__(self):
		self.path_id = -1
		self.unity_type = None
		self.size = -1
		self.name = None

	def set_name(self, obj, asset_bundle_data: AssetDependencyAssetBundleData):
		# try to avoid obj.read's, which will cause chunks to get compressed as needed
		if asset_bundle_data is not None:
			if self.path_id in asset_bundle_data.export_names_by_path_id:
				self.name = asset_bundle_data.export_names_by_path_id[self.path_id]
				return

		name = obj.read_name_only()
		if name is not None:
			self.name = name['m_Name']

class AssetDependencyTable:
	def __init__(self):
		self.source_file = None
		self.name = None
		self.preload_data = None
		self.asset_bundle_data = None
		self.external_refs = []
		self.objects = {}

	def setup(self, asset: Asset):
		self.name = asset.name

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


class AssetDependencyDatabase:
	def __init__(self):
		self.dependency_table = []

	def build_from_bundle(self, source_file: str, bundle: AssetBundle):
		for asset in bundle.assets:
			self.add_asset(source_file, asset)

	def add_asset(self, source_file: str, asset: Asset):
		table = AssetDependencyTable()
		table.source_file = source_file
		table.setup(asset)

	def write_to_json_file(self, json_path):
		with open(json_path, "w") as json_file:
			json_file.write(json.dumps(self, indent=4, default=to_serializable))
