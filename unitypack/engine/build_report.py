from enum import IntEnum
from .component import Component
from .object import Object, field, field_list, field_dict


class BuildReportPackedAssetInfo(Object):
	fileID = field("fileID", int) #SInt64
	classID = field("classID", int)
	packedSize = field("packedSize", int)
	sourceAssetGUID = field("sourceAssetGUID")
	buildTimeAssetPath = field("buildTimeAssetPath", str)


class PackedAssets(Object):
	m_File = field("m_File", int) #unsigned
	m_ShortPath = field("m_ShortPath", str)
	m_Overhead = field("m_Overhead", int) #UInt64
	m_Contents = field_list("m_Contents", BuildReportPackedAssetInfo)


class BuildSummary(Object):
	name = field("name", str)
	buildGUID = field("buildGUID")
	platformName = field("platformName", str)
	platformGroupName = field("platformGroupName", str)
	options = field("options", int)
	assetBundleOptions = field("assetBundleOptions", int)
	outputPath = field("outputPath", str)
	crc = field("crc", int) #uint
	totalSize = field("totalSize", int) #UInt64
	totalTimeMS = field("totalTimeMS", int) #UInt64
	totalErrors = field("totalErrors", int)
	totalWarnings = field("totalWarnings", int)
	buildType = field("buildType", int)
	success = field("success", bool)


class BuildReportFile(Object):
	path = field("path", str)
	role = field("role", str)
	id = field("id", int) #uint
	totalSize = field("totalSize", int) #UInt64


class BuildStepMessage(Object):
	type = field("type", int)
	content = field("content", int)


class BuildStepInfo(Object):
	stepName = field("stepName", str)
	duration = field("duration", int) #UInt64
	messages = field_list("messages", BuildStepMessage)


class BuildReport(Object):
	m_ObjectHideFlags = field("m_ObjectHideFlags", int) #unsigned
	m_PrefabParentObject = field("m_PrefabParentObject") #EditorExtension
	m_PrefabInternal = field("m_PrefabInternal") #Prefab
	m_Summary = field("m_Summary", BuildSummary)
	m_Files = field_list("m_Files", BuildReportFile)
	m_BuildSteps = field_list("m_BuildSteps", BuildStepInfo)
	m_Appendices = field_list("m_Appendices")