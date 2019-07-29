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

import io
import png
import json
import math
from NamedStruct import NamedStruct

class Palette():
	def __init__(self, colors):
		self._colors = colors
		self._index_by_color = { rgb: index for (index, rgb) in enumerate(self._colors) }

	@staticmethod
	def rgb_diff(rgb1, rgb2):
		return math.sqrt((rgb1[0] - rgb2[0]) ** 2 + (rgb1[1] - rgb2[1]) ** 2 + (rgb1[2] - rgb2[2]) ** 2)

	def _lookup_closest(self, rgb):
		best_index = 0
		best_error = px_diff(rgb, self._colors[best_index])
		for (index, pixel) in enumerate(self._colors[1:], 1):
			error = px_diff(rgb, pixel)
			if error < best_error:
				best_error = error
				best_index = index
		return best_index

	def lookup(self, rgb):
		if rgb in self._index_by_color:
			return self._index_by_color[rgb]
		else:
			return self._lookup_closest(rgb)

	@classmethod
	def load_from_json(cls, filename):
		with open(filename) as f:
			colors = json.load(f)
		colors = [ (int(color[0 : 2], 16), int(color[2 : 4], 16), int(color[4 : 6], 16)) for color in colors ]
		return cls(colors)

	def __getitem__(self, index):
		return self._colors[index]

class EncoderImage():
	name = "image"
	_HEADER = NamedStruct((
		("h",	"width"),
		("h",	"height"),
		("h",	"offsetx"),
		("h",	"offsety"),
	))
	_POINTER = NamedStruct((
		("l",	"offset"),
	))
	_SPANHDR = NamedStruct((
		("B",	"yoffset"),
		("B",	"pixel_cnt"),
		("B",	"dummy"),
	))
	_Palette = None

	@classmethod
	def _generate_palette(cls):
		if cls._Palette is not None:
			return
		cls._Palette = Palette.load_from_json("palette.json")

	@classmethod
	def decode(cls, encoded_data):
		cls._generate_palette()
		decoded_data = encoded_data
		header = cls._HEADER.unpack_head(encoded_data)

		start_ptrs = [ ]
		offset = cls._HEADER.size
		for x in range(header.width):
			start_ptr = cls._POINTER.unpack_head(encoded_data[offset : ])
			start_ptrs.append(start_ptr)
			offset += cls._POINTER.size

		(img_width, img_height) = (header.width, header.height)
		raw_pixel_data = bytearray(4 * img_width * img_height)
		for (x, start_ptr) in enumerate(start_ptrs):
			offset = start_ptr.offset
			ybase = 0
			while True:
				if encoded_data[offset] == 255:
					break
				span_hdr = cls._SPANHDR.unpack_head(encoded_data[offset : ])
				offset += cls._SPANHDR.size
				for y in range(span_hdr.pixel_cnt):
					pixel_index = encoded_data[offset + y]
					pixel_offset = 4 * (x + ((y + span_hdr.yoffset) * header.width))
					pixel_value = cls._Palette[pixel_index]
					for i in range(3):
						raw_pixel_data[pixel_offset + i] = pixel_value[i]
					raw_pixel_data[pixel_offset + 3] = 0xff
				offset += span_hdr.pixel_cnt + 1

		row_data = [ raw_pixel_data[x : x + (4 * img_width)] for x in range(0, len(raw_pixel_data), 4 * img_width) ]
		iobuf = io.BytesIO()
		png_image = png.from_array(row_data, mode = "RGBA", info = { "width": header.width, "height": header.height })
		png_image.write(iobuf)
		decoded_data = iobuf.getvalue()

		return decoded_data


	@classmethod
	def encode(cls, decoded_data):

		def encode_column(column):
			def emit(start_offset, values):
				return cls._SPANHDR.pack({
					"yoffset":		start_offset,
					"pixel_cnt":	len(values),
					"dummy":		0,
				}) + bytes(values)

			encoded_column = bytearray()
			start_offset = None
			chunk_data = [ ]
			fixed_offset = 0
			for (index, value) in enumerate(decoded_data):
				if value == -1:
					if start_offset is not None:
						# No more pixels, but we've seen some before
						fixed_offset = start_offset
						encoded_column += emit(start_offset - fixed_offset, chunk_data)
						start_offset = None
						chunk_data = [ ]
				else:
					# There's a pixel there
					if start_offset is None:
						# First pixel
						start_offset = index
						chunk_data = [ value ]
					else:
						# Subsequent pixel
						chunk_data.append(value)
						if len(chunk_data) >= 128:
							fixed_offset = start_offset
							encoded_column += emit(start_offset - fixed_offset, chunk_data)
							start_offset = None
							chunk_data = [ ]
			if start_offset is not None:
				encoded_column += emit(start_offset - fixed_offset, chunk_data)
			return encoded_column + b"\xff"

		cls._generate_palette()
		iobuf = io.BytesIO(decoded_data)
		(width, height, pixels, info) = png.Reader(file = iobuf).read_flat()

		encoded_data = bytearray()
		encoded_data += cls._HEADER.pack({
			"width":	width,
			"height":	height,
			"offsetx":	0,
			"offsety":	0,
		})

		column_offset = len(encoded_data) + (width * cls._POINTER.size)
		column_data = bytearray()

		column_offset = 0
		for x in range(width):
			col_data = [ ]
			for y in range(height):
				pixel_offset = 4 * (x + (y * width))
				(rgb, a) = (tuple(pixels[pixel_offset + 0 : pixel_offset + 3]), pixels[pixel_offset + 3])
				if a == 255:
					pixel_index = cls._Palette.lookup(rgb)
				else:
					pixel_index = -1
				col_data.append(pixel_index)

			encoded_col_data = encode_column(col_data)
			column_data += encoded_col_data
			encoded_data += cls._POINTER.pack({
				"offset":	column_offset,
			})
			column_offset += len(encoded_col_data)

		encoded_data += column_data

		return encoded_data
