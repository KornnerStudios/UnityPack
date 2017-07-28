#!/usr/bin/env python
import os
import pickle
import sys
import unitypack
from argparse import ArgumentParser
from io import BytesIO
from unitypack.asset import Asset
from unitypack.export import OBJMesh
from unitypack.utils import extract_audioclip_samples
from unitypack.asset_dependencies import AssetDependencyDatabase
import json

class UnityAssetStats:
	FORMAT_ARGS = {
		"audio": "AudioClip",
		"fonts": "Font",
		"images": "Texture2D",
		"models": "Mesh",
		"shaders": "Shader",
		"text": "TextAsset",
		"video": "MovieTexture",
		"asset_bundles": "AssetBundle",
		"preload_data": "PreloadData",
	}
	BUILT_IN_ASSETS = [
		"unity default resources",
		"unity_builtin_extra"
	]
	def find_built_in_assets_index(self, filename) -> int:
		index = 0
		for built_in_name in self.BUILT_IN_ASSETS:
			if filename.find(built_in_name) >= 0:
				return index
			index += 1
		return -1

	def __init__(self, args):
		self.parse_args(args)
		self.json_data = {}
		self.dependency_db = None

	def parse_args(self, args):
		p = ArgumentParser()
		p.add_argument("--verbose", action="store_true", help="")
		p.add_argument("files", nargs="*")
		p.add_argument("--all", action="store_true", help="Extract all supported types")
		for arg, clsname in self.FORMAT_ARGS.items():
			p.add_argument("--" + arg, action="store_true", help="Extract %s" % (clsname))
		p.add_argument("-o", "--outdir", nargs="?", default="", help="Output directory")
		p.add_argument("--as-asset", action="store_true", help="Force open files as Asset format")
		p.add_argument("-n", "--dry-run", action="store_true", help="Skip writing files")
		p.add_argument("--path_to_resources", nargs="?", default="", help="Should be the Resource subfolder of path_to_assets")
		p.add_argument("--path_to_assets", nargs="?", default="", help="Directory containing .asset files to process")
		p.add_argument("--path_to_asset_bundles", nargs="?", default="", help="Directory containing .manifest files for asset bundles to process")

		p.add_argument("--sort_objects", action="store_true", help="")

		p.add_argument("--dep_summary", action="store_true", help="")

		p.add_argument("--art_dump", action="store_true", help="Dump info about art files (Textures, Meshes)")

		p.add_argument("--art_dump_summary", action="store_true", help="Build a summary of from dumped art files info")
		p.add_argument("--min_instances_count", type=int, nargs='?', default=-1,
			help="When dumping a summary, marks the min InstancesCount for an asset to be listed for auto bundling scripts")
		p.add_argument("--min_image_size", type=int, nargs='?', default=-1,
			help="When dumping a summary, marks the min ImageSize for an asset to be listed for auto bundling scripts")

		self.args = p.parse_args(args)

		self.handle_formats = []
		for a, classname in self.FORMAT_ARGS.items():
			if self.args.all or getattr(self.args, a):
				self.handle_formats.append(classname)

	def run(self):
		files = self.args.files

		self.populate_files_with_resource_assets(files)
		self.populate_files_with_asset_levels(files)
		self.populate_files_with_assets(files)
		self.populate_files_with_asset_bundles(files)

		# initialize object data for art_dump_summary
		if self.args.art_dump_summary:
			self.art_dump_textures_summary = {}
			self.art_dump_meshes_summary = {}
			self.art_dump_animation_clips_summary = {}
			self.art_dump_shaders_summary = {}
			self.art_dump_textures_size = 0
			self.art_dump_meshes_size = 0
			self.art_dump_animation_clips_size = 0
			self.art_dump_shaders_size = 0
		elif self.args.dep_summary:
			self.dependency_db = AssetDependencyDatabase()

		for file in files:
			if self.args.dep_summary:
				print("Processing " + file + "...", flush=True)
			else:
				print("Processing " + file + "...", end='', flush=True)

			# reset the write_json_data flag during art_dump. It is flipped when there are art assets found
			if self.args.art_dump:
				self.write_json_data = False

			if self.args.art_dump_summary:
				with open(file, "r") as f:
					self.handle_file_for_art_dump_summary(file, f)
				print("Done")
				continue

			# reset the json_data dict working memory on each file
			self.json_data = {}
			self.write_json_data = True

			if self.args.as_asset or file.endswith(".assets") or file.find("\\level") >= 0 or self.find_built_in_assets_index(file) >= 0:
				with open(file, "rb") as f:
					asset = Asset.from_file(f)

					self.json_data['Path'] = file

					# setup the ArtDump dictionary for handle_asset_for_art_dump
					if self.args.art_dump:
						self.json_data['ArtDump'] = {}
					elif self.args.dep_summary:
						self.dependency_db.add_asset(file, asset)
						continue

					if self.args.art_dump:
						self.handle_asset_for_art_dump(file, asset)
					else:
						self.handle_asset(file, asset)

					if not self.args.dry_run:
						json_path = file + ".json"
						if self.write_json_data:
							with open(json_path, "w") as json_file:
								json_file.write(json.dumps(self.json_data, indent=4))
						else:
							print("Not writing JSON...", end='')

				print("Done")
				continue

			with open(file, "rb") as f:
				bundle = unitypack.load(f)

				self.json_data['Path'] = bundle.path
				self.json_data['GeneratorVersion'] = bundle.generator_version
				self.json_data['CompressionType'] = str(bundle.compression_type).replace(str("CompressionType."), "")
				self.json_data['FileSize'] = bundle.file_size
				self.json_data['BlockStorageFileOffset'] = bundle.block_storage_file_offset

				# setup the ArtDump dictionary for handle_asset_for_art_dump
				if self.args.art_dump:
					self.json_data['ArtDump'] = {}
				elif self.args.dep_summary:
					self.dependency_db.build_from_bundle(file, bundle)
					continue

				for asset in bundle.assets:
					if self.args.art_dump:
						self.handle_asset_for_art_dump(file, asset)
					else:
						self.handle_asset(file, asset)

				if not self.args.dry_run:
					json_path = file + ".json"
					if self.write_json_data:
						with open(json_path, "w") as json_file:
							json_file.write(json.dumps(self.json_data, indent=4))
					else:
						print("Not writing JSON...", end='')

			print("Done")

		if self.args.art_dump_summary:
			print("Writing art dump summary " + "" + "...", end='')
			self.write_art_dump_summary()
			print("Done")
		elif self.args.dep_summary:
			if self.dependency_db is not None:
				summary_path = self.get_output_path("dependency_summary" + ".json")
				print("Writing dependency summary " + "" + "...", end='', flush=True)
				self.dependency_db.write_to_json_file(summary_path)
				print("Done")

		return 0

	def populate_files_with_asset_levels(self, files):
		if len(self.args.path_to_assets) == 0:
			return

		file_ex = ''
		if self.args.art_dump_summary:
			file_ex = '.json'

		for f in os.listdir(self.args.path_to_assets):
			if f.startswith("level"):
				if not self.args.art_dump_summary and f.endswith('.json'):
					continue
				if self.args.art_dump_summary and not f.endswith('.json'):
					continue
				files.append(os.path.join(self.args.path_to_assets, f))

		#for file in [f for f in os.listdir(self.args.path_to_assets) if f.startswith("level")]:
		#	if not self.args.art_dump_summary and f.endswith('.json'):
		#		continue
		#	files.append(os.path.join(self.args.path_to_assets, file))

	def populate_files_with_assets(self, files):
		if len(self.args.path_to_assets) == 0:
			return

		file_ex = '.assets'
		if self.args.art_dump_summary:
			file_ex = '.json'

		for file in [f for f in os.listdir(self.args.path_to_assets) if f.endswith(file_ex)]:
			files.append(os.path.join(self.args.path_to_assets, file))

	def populate_files_with_resource_assets(self, files):
		if self.args.art_dump_summary:
			return
		if len(self.args.path_to_resources) == 0:
			return

		file_ex = "NO_FILE_EX"
		if not self.args.art_dump_summary:
			file_ex = '.json'

		for f in os.listdir(self.args.path_to_resources):
			if not f.endswith(file_ex) and self.find_built_in_assets_index(f) >= 0:
				files.append(os.path.join(self.args.path_to_resources, f))

	def populate_files_with_asset_bundles(self, files):
		if len(self.args.path_to_asset_bundles) == 0:
			return

		file_ex = '.manifest'
		if self.args.art_dump_summary:
			file_ex = '.json'

		for file in [f for f in os.listdir(self.args.path_to_asset_bundles) if f.endswith(file_ex) and not f.startswith("mega_textures")]:
			file = os.path.join(self.args.path_to_asset_bundles, file)
			file = file.replace(".manifest", "")
			files.append(file)

	def get_output_path(self, filename):
		basedir = os.path.abspath(self.args.outdir)
		path = os.path.join(basedir, filename)
		dirs = os.path.dirname(path)
		if not os.path.exists(dirs):
			os.makedirs(dirs)
		return path

	def write_to_file(self, filename, contents, mode="w"):
		path = self.get_output_path(filename)

		if self.args.dry_run:
			print("Would write %i bytes to %r" % (len(contents), path))
			return

		with open(path, mode) as f:
			written = f.write(contents)

		print("Written %i bytes to %r" % (written, path))

	def write_asset_bundle_to_file(self, asset_file_path, asset_bundle_obj, asset_bundle):
		#asset_file_name = os.path.splitext(asset_file_path)[0]
		#path = self.get_output_path(asset_file_name + ".json")
		path = asset_file_path + ".json"

		with open(path, "w") as f:
			f.write(asset_bundle.to_json(asset_bundle_obj))

		return

	def handle_asset(self, asset_file_path, asset):
		objects_json = []
		asset_json = ({
			'Name': asset.name,
			'ExternalRefs': asset.external_refs_to_file_path_list(),
		})
		self.json_data[asset.name] = asset_json

		bundle = asset.bundle
		block_storage_file_offset = 0
		if bundle is not None:
			block_storage_file_offset = bundle.block_storage_file_offset

		for id, obj in asset.objects.items():
			if obj.type_tree is None:
				if self.args.verbose:
					print("Skipping unrecongized Object: #{0} class={1} data_offset={2}, size={3}".format(id, obj.class_id, obj.data_offset, obj.size))
				continue

			obj_json = None

			if obj.type == "Shader" and id != 2841:
				d = obj.read()
				d = d

			if obj.type == "AssetBundle":
				d = obj.read()
				obj_json = d.to_json_data(obj)
				asset_json[obj.type] = obj_json
				continue
			elif obj.type == "PreloadData":
				d = obj.read()
				obj_json = d.to_json_data(obj)
				asset_json[obj.type] = obj_json
				continue
			else:
				#d = obj.read()
				d = obj.read_name_only()
				name = None
				if d is None:
					pass
				elif hasattr(d, 'name'):
					name = d.name
				else:
					name = d['m_Name']

				obj_json = ({
					'PathId': obj.path_id,
					'name': name,
					'UnityType': obj.type,
					'Size': obj.size,
					#'OffsetInBlock': obj.data_offset,
					'OffsetInFile': block_storage_file_offset + obj.data_offset,
				})
				objects_json.append(obj_json)
				continue

			if obj_json is not None:
				key = obj.type
				if hasattr(obj, 'name'):
					key = obj.name
				asset_json[key] = obj_json

		if self.args.sort_objects:
			objects_json.sort(key=lambda x: x['Size'], reverse=True)

		asset_json['Objects'] = objects_json

	def handle_asset_for_art_dump(self, asset_file_path, asset):

		art_dict = ({
			'Texture2D': ({
				'TotalSize': 0,
				'TotalRealSize': 0,
				'Objects': [],
			}),
			'Mesh': ({
				'TotalSize': 0,
				'TotalRealSize': 0,
				'Objects': [],
			}),
			'AnimationClip': ({
				'TotalSize': 0,
				'TotalRealSize': 0,
				'Objects': [],
			}),
			'Shader': ({
				'TotalSize': 0,
				'TotalRealSize': 0,
				'Objects': [],
			}),
		})
		desired_art_types = list(art_dict.keys())

		asset_objects_count = len(asset.objects)

		for id, obj in asset.objects.items():
			if obj.type_tree is None:
				if self.args.verbose:
					print("Skipping unrecongized Object: #{0} class={1} data_offset={2}, size={3}".format(id, obj.class_id, obj.data_offset, obj.size))
				continue

			'''
			if obj.type == "AssetBundle":
				d = obj.read()
				art_dict[obj.type] = d.to_json_data(obj)
			elif obj.type == "PreloadData":
				d = obj.read()
				art_dict[obj.type] = d.to_json_data(obj)
			'''

			if obj.type not in desired_art_types:
				continue

			d = None
			name = None

			if obj.type == 'Texture2D':
				d = obj.read()
				name = d.name
			else:
				d = obj.read_name_only()
				if d is None:
					if self.args.verbose:
						print("Did not read a name for Object {0} {1} {2}".format(id, obj.type))
					continue
				name = d['m_Name']

			if (
				name.startswith("Lightmap-") or
				name.startswith("Combined Mesh")
				): continue

			if obj.type == 'Texture2D':
				name = name + "." + str(d.complete_image_size)
			elif obj.path_id < 0 or obj.path_id > asset_objects_count:
				name = name + "." + str(obj.path_id)

			object_dict = art_dict[obj.type]
			objects_list = object_dict['Objects']

			obj_size = obj.size
			obj_real_size = obj_size

			# update Objects
			object_info = ({
				'Name': name,
				'Size': obj_size,
			})
			if obj.type == 'Texture2D':
				object_info['ImageSize'] = d.complete_image_size
				object_info['Height'] = d.height
				object_info['Width'] = d.width
				object_info['Format'] = str( d.format ).replace("TextureFormat.", "")
				object_info['Dimension'] = str( d.texture_dimension ).replace("TextureDimension.", "")
				if d.is_readable:
					object_info['IsReadable'] = True
				# texture data in .assets may exist outside the file, and so the the obj.size doesn't represent the number we desire in our TotalSize
				if obj_size < d.complete_image_size:
					# texture exists elsewhere
					if asset.bundle is not None:
						continue
					obj_size = d.complete_image_size

			objects_list.append(object_info)
			# update TotalSize
			objects_total_size = object_dict['TotalSize']
			objects_total_size += obj_size
			object_dict['TotalSize'] = objects_total_size

			objects_total_real_size = object_dict['TotalRealSize']
			objects_total_real_size += obj_real_size
			object_dict['TotalRealSize'] = objects_total_real_size

		for key, value in art_dict.items():
			if 'Objects' not in value:
				continue
			objects_list = value['Objects']
			objects_list.sort(key=lambda x: x['Size'], reverse=True)
			if not self.write_json_data:
				self.write_json_data = len(objects_list) > 0

		art_dump = self.json_data['ArtDump']
		art_dump[asset.name] = art_dict

	def handle_file_for_art_dump_summary(self, json_file_path, json_file):
		json_obj = json.load(json_file)
		source_file = json_obj['Path']
		json_art_dump_obj = json_obj['ArtDump']

		for unity_file_name, json_art_data in json_art_dump_obj.items():
			source_name = unity_file_name
			if source_name.startswith("CAB-"):
				source_name = source_file
			self.art_dump_textures_size += self.handle_art_data_for_art_dump_summary(source_name, json_art_data, 'Texture2D', self.art_dump_textures_summary)
			self.art_dump_meshes_size += self.handle_art_data_for_art_dump_summary(source_name, json_art_data, 'Mesh', self.art_dump_meshes_summary)
			self.art_dump_animation_clips_size += self.handle_art_data_for_art_dump_summary(source_name, json_art_data, 'AnimationClip', self.art_dump_animation_clips_summary)
			self.art_dump_shaders_size += self.handle_art_data_for_art_dump_summary(source_name, json_art_data, 'Shader', self.art_dump_shaders_summary)

	def handle_art_data_for_art_dump_summary(self, unity_file_name, json_art_data, art_key, art_key_summary):
		if art_key not in json_art_data:
			return

		json_art_key_data = json_art_data[art_key]
		json_art_objects = json_art_key_data['Objects']
		json_art_total_size = json_art_key_data['TotalRealSize']

		for art_obj in json_art_objects:
			art_obj_name = art_obj['Name']
			art_obj_size = art_obj['Size']

			art_obj_summary	= None
			if art_obj_name not in art_key_summary:
				art_key_summary[art_obj_name] = ({
					'Name': art_obj_name,
					'Size': art_obj_size,
				})
				art_obj_summary = art_key_summary[art_obj_name]
				if art_key == "Texture2D":
					art_obj_summary['ImageSize'] = art_obj['ImageSize']
					art_obj_summary['Height'] = art_obj['Height']
					art_obj_summary['Width'] = art_obj['Width']
					art_obj_summary['Format'] = art_obj['Format']
					art_obj_summary['Dimension'] = art_obj['Dimension']
					if 'IsReadable' in art_obj:
						art_obj_summary['IsReadable'] = art_obj['IsReadable']
				art_obj_summary['InstancesCount'] = 0
				art_obj_summary['Instances'] = []
			else:
				art_obj_summary = art_key_summary[art_obj_name]

			art_obj_summary_instances = art_obj_summary['Instances']

			art_obj_summary_instances.append(unity_file_name)
			art_obj_summary_instances_count = art_obj_summary['InstancesCount']
			art_obj_summary_instances_count += 1
			art_obj_summary['InstancesCount'] = art_obj_summary_instances_count

		return json_art_total_size

	def write_art_dump_summary(self):
		summary_path = self.get_output_path("art_dump_summary" + ".json")

		art_dump_textures_list = list(self.art_dump_textures_summary.values())
		art_dump_textures_list.sort(key=lambda x: (x['InstancesCount'], x['ImageSize']), reverse=True)

		art_dump_meshes_list = list(self.art_dump_meshes_summary.values())
		art_dump_meshes_list.sort(key=lambda x: (x['InstancesCount'], x['Size']), reverse=True)

		art_dump_animation_clips_list = list(self.art_dump_animation_clips_summary.values())
		art_dump_animation_clips_list.sort(key=lambda x: (x['InstancesCount'], x['Size']), reverse=True)

		art_dump_shaders_list = list(self.art_dump_shaders_summary.values())
		art_dump_shaders_list.sort(key=lambda x: (x['InstancesCount'], x['Size']), reverse=True)

		self.art_dump_summary = ({
			'DumpFiles': self.args.files,
			'SizeOfTexture2D': self.art_dump_textures_size,
			'SizeOfMesh': self.art_dump_meshes_size,
			'SizeOfAnimationClip': self.art_dump_animation_clips_size,
			'SizeOfShader': self.art_dump_shaders_size,
			'Texture2D': art_dump_textures_list,
			'Mesh': art_dump_meshes_list,
			'AnimationClip': art_dump_animation_clips_list,
			'Shader': art_dump_shaders_list,
			'AutoBundleScriptInputs': (
				self.generate_art_dump_summary_auto_bundle_script_inputs(art_dump_textures_list, "Texture2D") +
				self.generate_art_dump_summary_auto_bundle_script_inputs(art_dump_meshes_list, "Mesh")
			),
		})

		with open(summary_path, "w") as json_file:
			json_file.write(json.dumps(self.art_dump_summary, indent=4))

	def generate_art_dump_summary_auto_bundle_script_inputs(self, asset_list: list, asset_type: str) -> list:
		if asset_type != "Texture2D":
			return []

		if self.args.min_instances_count < 0 and self.args.min_image_size:
			return []

		script_inputs = []

		for asset in asset_list:
			name, instances_count, image_size = asset['Name'], asset['InstancesCount'], asset['ImageSize']
			if self.args.min_instances_count < 0 or self.args.min_instances_count > instances_count:
				continue
			if self.args.min_image_size < 0 or self.args.min_image_size > image_size:
				continue

			name_dot_index = name.rfind('.')
			if name_dot_index == -1:
				print("BAD NAME! NO '.': %r" % name)
				continue

			name = name[:name_dot_index]

			input = "{0} t:{1}".format(name, asset_type)
			script_inputs.append(input)

		return script_inputs



def main():
	app = UnityAssetStats(sys.argv[1:])
	result = app.run()
	exit(result)


if __name__ == "__main__":
	main()
