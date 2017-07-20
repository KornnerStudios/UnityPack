from enum import IntEnum
from .component import Component
from .object import Object, field
import json

class AssetInfo(Object):
	preloadIndex = field("preloadIndex", int)
	preloadSize = field("preloadSize", int)
	asset = field("asset")

class AssetBundle(Object):
	m_PreloadTable = field("m_PreloadTable")
	m_Container = field("m_Container", dict)
	m_MainAsset = field("m_MainAsset")
	m_AssetBundleName = field("m_AssetBundleName")
	m_Dependencies = field("m_Dependencies")

	def __str__(self):
		return self.m_AssetBundleName

	def to_json(self, asset_bundle_obj):
		bundle = asset_bundle_obj.asset.bundle
		json_data = ({
				'name': self.name,
				'Path': bundle.path,
				'AssetBundleName': self.m_AssetBundleName,
				'Dependencies': self.m_Dependencies,
				'Compressed': bundle.compressed,
				'FileSize': bundle.file_size,
				'GeneratorVersion': bundle.generator_version,
				'BlockStorageFileOffset': bundle.block_storage_file_offset,
			})
		
		container_dict = {}
		for path, asset_info in self.m_Container.items():
			obj_ptr = asset_info['asset']
			obj = obj_ptr.object
			value = ({
					'PathId': obj_ptr.file_id,
					'UnityType': obj.type,
					'Size': obj.size,
					'OffsetInBlock': obj.data_offset,
					'OffsetInFile': bundle.block_storage_file_offset + obj.data_offset,
				})
			container_dict[path] = value

		json_data['Container'] = container_dict

		return json.dumps(json_data, indent=4)
