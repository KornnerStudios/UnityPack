from enum import IntEnum, IntFlag
from typing import List
from .component import Component
from .object import Object, field, field_list
from .texture import TextureDimension


class SerializedSubShader(Object):
	m_Passes = field("m_Passes")
	m_Tags = field("m_Tags")
	m_LOD = field("m_LOD")


class SerializedTextureProperty(Object):
	m_DefaultName = field("m_DefaultName")
	m_TexDim = field("m_TexDim", TextureDimension)


class SerializedPropertyType(IntEnum):
	Color = 0
	Vector = 1
	Float = 2
	Range = 3
	Texture = 4


class SerializedPropertyFlags(IntFlag):
	HideInInspector = (1<<0)
	PerRendererData = (1<<1)
	NoScaleOffset = (1<<2)
	Normal = (1<<3)
	HDR = (1<<4)
	Gamma = (1<<5)


class SerializedProperty(Object):
	m_Description = field("m_Description")
	m_Attributes = field_list("m_Attributes", str)
	m_Type = field("m_Type", SerializedPropertyType)
	m_Flags = field("m_Flags", SerializedPropertyFlags)
	m_DefValue0 = field("m_DefValue[0]", float)
	m_DefValue1 = field("m_DefValue[1]", float)
	m_DefValue2 = field("m_DefValue[2]", float)
	m_DefValue3 = field("m_DefValue[3]", float)
	m_DefTexture = field("m_DefTexture", SerializedTextureProperty)

	def __repr__(self):
		return "<%s %s %s>" % (self.__class__.__name__, self.m_Type, self.name)


class SerializedProperties(Object):
	m_Props = field_list("m_Props", SerializedProperty)


class SerializedShaderDependency(Object):
	m_From = field("from")
	m_To = field("to")


class SerializedShader(Object):
	m_PropInfo = field("m_PropInfo", SerializedProperties)
	m_SubShaders = field_list("m_SubShaders", SerializedSubShader)
	m_Name = field("m_Name")
	m_CustomEditorName = field("m_CustomEditorName")
	m_FallbackName = field("m_FallbackName")
	m_Dependencies = field_list("m_Dependencies", SerializedShaderDependency)
	m_DisableNoSubshadersMessage = field("m_DisableNoSubshadersMessage")

	def __repr__(self):
		return "<%s %s: %s, %s>" % (self.__class__.__name__, self.name, self.m_CustomEditorName, self.m_FallbackName)


class Shader(Object):
	m_ParsedForm = field("m_ParsedForm", SerializedShader)
	platforms = field("platforms")
	offsets = field_list("offsets")
	compressedLengths = field("compressedLengths")
	decompressedLengths = field("decompressedLengths")
	m_Dependencies = field("m_Dependencies")
	m_ShaderIsBaked = field("m_ShaderIsBaked", bool)
