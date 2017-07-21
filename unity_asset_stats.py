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

	def __init__(self, args):
		self.parse_args(args)
		self.json_data = {}

	def parse_args(self, args):
		p = ArgumentParser()
		p.add_argument("files", nargs="+")
		p.add_argument("--all", action="store_true", help="Extract all supported types")
		for arg, clsname in self.FORMAT_ARGS.items():
			p.add_argument("--" + arg, action="store_true", help="Extract %s" % (clsname))
		p.add_argument("-o", "--outdir", nargs="?", default="", help="Output directory")
		p.add_argument("--as-asset", action="store_true", help="Force open files as Asset format")
		p.add_argument("--filter", nargs="*", help="Filter extraction for a specific name")
		p.add_argument("-n", "--dry-run", action="store_true", help="Skip writing files")
		p.add_argument("--art_dump", action="store_true", help="Dump info about art files (Textures, Meshes)")
		self.args = p.parse_args(args)

		self.handle_formats = []
		for a, classname in self.FORMAT_ARGS.items():
			if self.args.all or getattr(self.args, a):
				self.handle_formats.append(classname)

	def run(self):
		for file in self.args.files:
			# reset the json_data dict working memory on each file
			self.json_data = {}

			if self.args.as_asset or file.endswith(".assets"):
				with open(file, "rb") as f:
					asset = Asset.from_file(f)

					self.json_data['Path'] = file

					# setup the ArtDump dictionary for handle_asset_for_art_dump
					if self.args.art_dump:
						self.json_data['ArtDump'] = {}

					if self.args.art_dump:
						self.handle_asset_for_art_dump(file, asset)
					else:
						self.handle_asset(file, asset)

					if not self.args.dry_run:
						json_path = file + ".json"
						with open(json_path, "w") as json_file:
							json_file.write(json.dumps(self.json_data, indent=4))

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

				for asset in bundle.assets:
					if self.args.art_dump:
						self.handle_asset_for_art_dump(file, asset)
					else:
						self.handle_asset(file, asset)

				if not self.args.dry_run:
					json_path = file + ".json"
					with open(json_path, "w") as json_file:
						json_file.write(json.dumps(self.json_data, indent=4))

		return 0

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
		objects_json = {}

		for id, obj in asset.objects.items():
			if obj.type_tree is None:
				print("Skipping unrecongized Object: #{0} class={1} data_offset={2}, size={3}".format(id, obj.class_id, obj.data_offset, obj.size))
				continue

			if self.args.dry_run:
				if obj.type == "Texture2D":
					d = obj.read_name_only()
					name = None
					if d is None:
						pass
					elif hasattr(d, 'name'):
						name = d.name
					else:
						name = d['m_Name']
					print("Object {0} {1} {2}".format(id, obj.type, name))
				continue

			if self.args.dry_run:
				name = "NULL"
				if hasattr(obj, 'name'):
					name = obj.name
				print("Object {0} {1} {2}".format(id, obj.type, name))

			obj_json = None

			if obj.type == "AssetBundle":
				d = obj.read()
				obj_json = d.to_json_data(obj)
			elif obj.type == "PreloadData":
				d = obj.read()
				obj_json = d.to_json_data(obj)
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
					'OffsetInBlock': obj.data_offset,
				})
				objects_json[id] = obj_json
				continue

			if obj_json is not None:
				key = obj.type
				if hasattr(obj, 'name'):
					key = obj.name
				self.json_data[key] = obj_json

		self.json_data['Objects'] = objects_json

	def handle_asset_for_art_dump(self, asset_file_path, asset):

		art_dict = ({
			'Texture2D': ({
				'TotalSize': 0,
				'Objects': [],
			}),
			'Mesh': ({
				'TotalSize': 0,
				'Objects': [],
			})
		})

		for id, obj in asset.objects.items():
			if obj.type_tree is None:
				print("Skipping unrecongized Object: #{0} class={1} data_offset={2}, size={3}".format(id, obj.class_id, obj.data_offset, obj.size))
				continue

			if obj.type not in art_dict:
				continue

			d = obj.read_name_only()
			if d is None:
				print("Did not read a name for Object {0} {1} {2}".format(id, obj.type))
				continue
			name = d['m_Name']

			object_dict = art_dict[obj.type]
			objects_list = object_dict['Objects']

			# update Objects
			object_info = ({
				'Name': name,
				'Size': obj.size,
			})
			objects_list.append(object_info)
			# update TotalSize
			objects_total_size = object_dict['TotalSize']
			objects_total_size += obj.size
			object_dict['TotalSize'] = objects_total_size

		for key, value in art_dict.items():
			objects_list = value['Objects']
			objects_list.sort(key=lambda x: x['Size'], reverse=True)

		art_dump = self.json_data['ArtDump']
		art_dump[asset.name] = art_dict



def main():
	app = UnityAssetStats(sys.argv[1:])
	result = app.run()
	exit(result)


if __name__ == "__main__":
	main()
