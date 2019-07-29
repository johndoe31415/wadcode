#	retools - Reverse engineering toolkit
#	Copyright (C) 2019-2019 Johannes Bauer
#
#	This file is part of retools.
#
#	retools is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	retools is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with retools; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import collections
import struct

class NamedStruct(object):
	def __init__(self, fields, struct_extra = "<"):
		struct_format = struct_extra + ("".join(fieldtype for (fieldtype, fieldname) in fields))
		self._struct = struct.Struct(struct_format)
		self._collection = collections.namedtuple("Fields", [ fieldname for (fieldtype, fieldname) in fields ])

	@property
	def size(self):
		return self._struct.size

	def pack(self, data):
		fields = self._collection(**data)
		return self._struct.pack(*fields)

	def unpack(self, data):
		values = self._struct.unpack(data)
		fields = self._collection(*values)
		return fields

	def unpack_head(self, data):
		return self.unpack(data[:self._struct.size])

	def unpack_from_file(self, f, at_offset = None):
		if at_offset is not None:
			f.seek(at_offset)
		data = f.read(self._struct.size)
		return self.unpack(data)
