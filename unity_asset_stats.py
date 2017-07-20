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
	}

	def __init__(self, args):
		self.parse_args(args)

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
		self.args = p.parse_args(args)

		self.handle_formats = []
		for a, classname in self.FORMAT_ARGS.items():
			if self.args.all or getattr(self.args, a):
				self.handle_formats.append(classname)

	def run(self):
		for file in self.args.files:
			if self.args.as_asset or file.endswith(".assets"):
				with open(file, "rb") as f:
					asset = Asset.from_file(f)
					self.handle_asset(asset)
				continue

			with open(file, "rb") as f:
				bundle = unitypack.load(f)

				for asset in bundle.assets:
					self.handle_asset(asset)

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

	def write_asset_bundle_to_file(self, asset_bundle_obj, asset_bundle):
		path = self.get_output_path(asset_bundle.m_AssetBundleName + "_stats.json")

		with open(path, "w") as f:
			f.write(asset_bundle.to_json(asset_bundle_obj))

		return

	def handle_asset(self, asset):
		for id, obj in asset.objects.items():
			d = obj.read()

			name = "NULL"
			if hasattr(obj, 'name'):
				name = obj.name

			if self.args.dry_run:
				print("Object {0} {1} {2}".format(id, obj.type, name))

			if obj.type == "AssetBundle":
				self.write_asset_bundle_to_file(obj, d)

def main():
	app = UnityAssetStats(sys.argv[1:])
	result = app.run()
	exit(result)


if __name__ == "__main__":
	main()
