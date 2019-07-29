#	wadcode - WAD compiler/decompiler for WAD resource files
#	Copyright (C) 2019-2019 Johannes Bauer
#
#	This file is part of wadcode.
#
#	wadcode is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	wadcode is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import os
import re
import json
import collections
import contextlib
from NamedStruct import NamedStruct
from EncoderImage import EncoderImage

class Filenames():
	def __init__(self):
		self._names = set()

	def generate(self, template, extension = ""):
		for i in range(1000):
			if i == 0:
				name = "%s%s" % (template, extension)
			else:
				name = "%s_%03d%s" % (template, i, extension)
			if name not in self._names:
				self._names.add(name)
				return name

class WADFile():
	_WAD_HEADER = NamedStruct((
		("4s", "magic"),
		("l", "number_of_files"),
		("l", "directory_offset"),
	))

	_FILE_ENTRY = NamedStruct((
		("l", "offset"),
		("l", "size"),
		("8s", "name"),
	))
	_WADResource = collections.namedtuple("WADResource", [ "name", "data" ])
	_Encoders = {
		encoder.name: encoder for encoder in [
			EncoderImage,
		]
	}

	def __init__(self):
		self._resources = [ ]
		self._resources_by_name = collections.defaultdict(list)

	def add_resource(self, resource):
		self._resources.append(resource)
		self._resources_by_name[resource.name].append(resource)

	@classmethod
	def create_from_file(cls, filename):
		wadfile = cls()
		with open(filename, "rb") as f:
			header = cls._WAD_HEADER.unpack_from_file(f)
			assert(header.magic == b"IWAD")

			f.seek(header.directory_offset)
			for fileno in range(header.number_of_files):
				fileinfo = cls._FILE_ENTRY.unpack_from_file(f)
				name = fileinfo.name.rstrip(b"\x00").decode("latin1")
				cur_pos = f.tell()
				f.seek(fileinfo.offset)
				data = f.read(fileinfo.size)
				f.seek(cur_pos)
				resource = cls._WADResource(name = name, data = data)
				wadfile.add_resource(resource)
		return wadfile

	@classmethod
	def create_from_directory(cls, dirname):
		wadfile = cls()
		content_json = dirname + "/content.json"
		with open(content_json) as f:
			content = json.load(f)

		for resource_info in content:
			if resource_info.get("virtual") is True:
				data = b""
			else:
				with open(dirname + "/files/" + resource_info["filename"], "rb") as f:
					data = f.read()

			if (len(data) > 0) and (resource_info.get("encoder") is not None):
				encoder_name = resource_info["encoder"]
				encoder_class = cls._Encoders[encoder_name]
				data = encoder_class.encode(data)

			resource = cls._WADResource(name = resource_info["name"], data = data)
			wadfile.add_resource(resource)
		return wadfile

	def write_to_directory(self, outdir, decode = False):
		with contextlib.suppress(FileExistsError):
			os.makedirs(outdir)
		output_json_filename = outdir + "/content.json"
		output_json = [ ]

		lvl_regex = re.compile("E\dM\d")
		fns = Filenames()
		section = None
		for resource in self._resources:
			resource_item = {
				"name":		resource.name,
			}
			if len(resource.data) == 0:
				resource_item["virtual"] = True
				section = resource.name
			else:
				extension = ""
				encoder = None
				template = resource.name.lower()
				if template.startswith("stcfn"):
					template = "font_small/%s" % (template)
				elif (template in [ "things", "linedefs", "sidedefs", "vertexes", "segs", "ssectors", "nodes", "sectors", "reject", "blockmap" ]) and (lvl_regex.fullmatch(section or "")):
					template = "level/%s/%s" % (section, template)
				elif decode and (any(template.startswith(x) for x in [ "stfdead", "stfkill", "stfouch", "stfst", "stftl", "stftr" ])):
					template = "face/%s" % (template)
					extension = ".png"
					encoder = EncoderImage
				elif decode and (any(template.startswith(x) for x in [ "titlepic" ])):
					template = "gfx/%s" % (template)
					extension = ".png"
					encoder = EncoderImage
				elif section is None:
					template = "nosection/%s" % (template)
				else:
					template = "other/%s" % (template)
				filename = fns.generate(template, extension)
				resource_item["filename"] = filename

				if encoder is not None:
					resource_item["encoder"] = encoder.name
					write_data = encoder.decode(resource.data)
				else:
					write_data = resource.data

				full_outname = "%s/files/%s" % (outdir, filename)
				with contextlib.suppress(FileExistsError):
					os.makedirs(os.path.dirname(full_outname))
				with open(full_outname, "wb") as outfile:
					outfile.write(write_data)

			output_json.append(resource_item)

		with open(output_json_filename, "w") as f:
			json.dump(output_json, fp = f, indent = 4, sort_keys = True)

	def write(self, wad_filename):
		with open(wad_filename, "wb") as f:
			directory_offset = self._WAD_HEADER.size
			header = self._WAD_HEADER.pack({
				"magic":			b"IWAD",
				"number_of_files":	len(self._resources),
				"directory_offset":	self._WAD_HEADER.size,
			})
			f.write(header)

			data_offset = directory_offset + (len(self._resources) * self._FILE_ENTRY.size)
			for resource in self._resources:
				file_entry = self._FILE_ENTRY.pack({
					"offset":	data_offset,
					"size":		len(resource.data),
					"name":		resource.name.encode("latin1"),
				})
				f.write(file_entry)
				data_offset += len(resource.data)
			for resource in self._resources:
				f.write(resource.data)
