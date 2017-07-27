from enum import IntEnum
from .component import Component
from .object import Object, field

class PreloadData(Object):
	m_Assets = field("m_Assets")
	m_Dependencies = field("m_Dependencies")

	def to_json_data(self, preload_data_obj):
		bundle = preload_data_obj.asset.bundle
		block_storage_file_offset = 0
		if bundle is not None:
			block_storage_file_offset = bundle.block_storage_file_offset

		this_json_data = ({
			'name': self.name,
			'Dependencies': self.m_Dependencies,
		})

		asset_list = []
		for obj_ptr in self.m_Assets:
			value = ({
				'FileId': obj_ptr.file_id,
				'PathId': obj_ptr.path_id,
			})

			asset_list.append(value)

		this_json_data['Assets'] = asset_list

		return this_json_data
