from enum import IntEnum
from .component import Component
from .object import Object, field, field_list, field_dict
from unitypack.resources import UnityClass


class BuildReport_C:
	pass


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

	def to_json_data(self):
		return PackedAssets_C(self)


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
	content = field("content", str)


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

	def to_json_data(self):
		return BuildReport_C(self)


class BuildReportPackedAssetInfo_C:
	def __init__(self, obj: BuildReportPackedAssetInfo):
		self.fileID = obj.fileID
		self.classID = UnityClass(obj.classID)
		self.packedSize = obj.packedSize
		self.sourceAssetGUID = obj.sourceAssetGUID
		self.buildTimeAssetPath = obj.buildTimeAssetPath
class PackedAssets_C:
	def __init__(self, obj: PackedAssets):
		self.m_File = obj.m_File
		self.m_ShortPath = obj.m_ShortPath
		self.m_Overhead = obj.m_Overhead
		self.m_Contents = [BuildReportPackedAssetInfo_C(o) for o in obj.m_Contents]
class BuildSummary_C:
	def __init__(self, obj: BuildSummary):
		self.name = obj.name
		self.buildGUID = obj.buildGUID
		self.platformName = obj.platformName
		self.platformGroupName = obj.platformGroupName
		self.options = obj.options
		self.assetBundleOptions = obj.assetBundleOptions
		self.outputPath = obj.outputPath
		self.crc = obj.crc
		self.totalSize = obj.totalSize
		self.totalTimeMS = obj.totalTimeMS
		self.totalErrors = obj.totalErrors
		self.totalWarnings = obj.totalWarnings
		self.buildType = obj.buildType
		self.success = obj.success
class BuildReportFile_C:
	def __init__(self, obj: BuildReportFile):
		self.path = obj.path
		self.role = obj.role
		self.id = obj.id
		self.totalSize = obj.totalSize
class BuildStepMessage_C:
	def __init__(self, obj: BuildStepMessage):
		self.type = obj.type
		self.content = obj.content
class BuildStepInfo_C:
	def __init__(self, obj: BuildStepInfo):
		self.stepName = obj.stepName
		self.duration = obj.duration
		self.messages = [BuildStepMessage_C(o) for o in obj.messages]
class BuildReport_C:
	def __init__(self, obj: BuildReport):
		self.m_Summary = BuildSummary_C(obj.m_Summary)
		self.m_Files = [BuildReportFile_C(o) for o in obj.m_Files]
		self.m_BuildSteps = [BuildStepInfo_C(o) for o in obj.m_BuildSteps]

