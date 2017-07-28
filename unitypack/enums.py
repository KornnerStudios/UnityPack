from enum import IntEnum


class CompressionType(IntEnum):
	NONE = 0
	LZMA = 1
	LZ4 = 2
	LZ4HC = 3
	LZHAM = 4


class NodeFlags(IntEnum):
	Default = 0
	Directory = 1
	Deleted = 2
	SerializedFile = 3


class RuntimePlatform(IntEnum):
	OSXEditor = 0
	OSXPlayer = 1
	WindowsPlayer = 2
	OSXWebPlayer = 3
	OSXDashboardPlayer = 4
	WindowsWebPlayer = 5
	WindowsEditor = 7
	IPhonePlayer = 8
	PS3 = 9
	XBOX360 = 10
	Android = 11
	NaCl = 12
	LinuxPlayer = 13
	FlashPlayer = 15
	WebGLPlayer = 17
	MetroPlayerX86 = 18
	WSAPlayerX86 = 18
	MetroPlayerX64 = 19
	WSAPlayerX64 = 19
	MetroPlayerARM = 20
	WSAPlayerARM = 20
	WP8Player = 21
	BB10Player = 22
	BlackBerryPlayer = 22
	TizenPlayer = 23
	PSP2 = 24
	PS4 = 25
	PSM = 26
	PSMPlayer = 26
	XboxOne = 27
	SamsungTVPlayer = 28
	WiiU = 30
	tvOS = 31
	Switch = 32

class BuildTargetPlatform(IntEnum):
	NoTargetPlatform = -2
	AnyPlayerData = -1
	ValidPlayer = 1
	#0
	StandaloneOSXUniversal = 2
	StandaloneOSXPPC = 3
	StandaloneOSXIntel = 4
	StandaloneWinPlayer = 5
	WebPlayerLZMA = 6
	WebPlayerLZMAStreamed = 7
	#8
	iPhone = 9
	DeprecatedPS3 = 10
	Xbox360 = 11
	Broadcom = 12
	Android = 13
	WinGLESEmu = 14
	WinGLES20Emu = 15
	NaCl = 16
	StandaloneLinux = 17
	Flash = 18
	StandaloneWin64Player = 19
	WebGL = 20
	MetroPlayer = 21
	#22
	#23
	StandaloneLinux64 = 24
	StandaloneLinuxUniversal = 25
	DeprecatedWP8Player = 26
	StandaloneOSXIntel64 = 27
	DeprecatedBB10 = 28
	Tizen = 29
	PSP2 = 30
	PS4 = 31
	PSM = 32
	XboxOne = 33
	SamsungTV = 34
	N3DS = 35
	WiiU = 36
	tvOS = 37
	Switch = 38