from enum import IntEnum
from .component import Component
from .object import Object, field

class AssetBundle(Object):
	m_PreloadTable = field("m_PreloadTable")
	m_Container = field("m_Container")
	m_MainAsset = field("m_MainAsset")
	m_AssetBundleName = field("m_AssetBundleName")
	m_Dependencies = field("m_Dependencies")

	def __str__(self):
		return self.m_AssetBundleName
