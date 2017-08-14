import os
import struct
import sys

from itertools import izip
from collections import namedtuple
from models import CARHeader, CARKeyFormat, CARKeyFormatIdentifier, \
                   CARRendition, CARFacet
from bom_models import BOMHeader, BOMBlock, BOMExtendedMetadata, BOMTree, \
                       BOMPath


BLOCK_CARHEADER = 'CARHEADER'
BLOCK_RENDITIONS = 'RENDITIONS'
BLOCK_FACET_KEYS = 'FACETKEYS'
BLOCK_KEY_FORMAT = 'KEYFORMAT'
BLOCK_EXTENDED_METADATA = 'EXTENDED_METADATA'
BLOCK_BITMAP_KEYS = 'BITMAPKEYS'
BLOCK_CAR_GLOBALS = 'CARGLOBALS'
BLOCK_EXTERNAL_KEYS = 'EXTERNAL_KEYS'
BLOCK_PART_INFO = "PART_INFO"
BLOCK_ELEMENT_INFO = "ELEMENT_INFO"
BLOCK_COLORS = "COLORS"
BLOCK_FONTS = "FONTS"
BLOCK_FONT_SIZES = "FONTSIZES"
BLOCK_GLYPHS = "GLYPHS"
BLOCK_BEZELS = "BEZELS"


class BOMInvalidFile(Exception):
    pass


StreamBlock = namedtuple("StreamBlock", ("stream", "block"))


class CARFile(object):
    """
    Compiled Asset Archive format (car)

    A car file is a specialized BOM file. It contains a bunch of named assets
    called "facets" and variants of them (renditions). New content types are
    added by blocks that are indexed on the table of contents at the end of
    the file. This class provides abstraction for the supported types
    (facets, renditions, etc) but you can also query unsupported types using
    `_stream_named`.
    """

    def __init__(self, path):
        """
        Parses a car file on a given file path. Note that this is not
        optimized and almost no parsing is lazy.

        - parameter path: The full path where the car file is located.
        """
        self.stream = open(path, "rb")
        self.path = path
        self.size = os.stat(path).st_size
        self._parse(self.stream)

    # - Public methods

    @property
    def header(self):
        """
        Information about the file contents, a version marker, and creator
        string. This is stored as a named structure indexed on the ToC.
        """
        return CARHeader.make(self._stream_named(BLOCK_CARHEADER).stream)

    @property
    def metadata(self):
        """
        Extra information about the file content (optimized flag, gamut, etc)
        """
        stream_block = self._stream_named(BLOCK_EXTENDED_METADATA)
        return BOMExtendedMetadata.make(stream_block.stream)

    @property
    def key_format(self):
        """
        Returns an array of supported key_format(s). Note that order is
        important since some blocks return an array values with the same order.
        """
        return CARKeyFormat.make(self._stream_named(BLOCK_KEY_FORMAT).stream)

    @property
    def renditions(self):
        """
        Stored as a BOMTree, it holds a list of attribute values, matching the
        order of attribute identifiers from `key_format`. Each rendition key
        is unique and has an identifier connecting it to the facet it beongs to
        """
        tree = BOMTree.make(self._stream_named(BLOCK_RENDITIONS).stream)
        identifiers = self.key_format.identifiers
        for key, value in tree.iterate(self._stream_index):
            attrs_values = [struct.unpack("<H", key[i:i + 2])[0]
                            for i in xrange(0, len(key), 2)]
            attributes = dict(izip(identifiers, attrs_values))
            yield CARRendition.make_from_buffer(value, attributes=attributes)

    @property
    def facets(self):
        """
        Stored as a BOMTree. Facets hold a name (string) and a list of
        attribute key-value pairs. Of those attributes, the `identifier` key
        is used to find the renditions comprising the facet.
        """
        tree = BOMTree.make(self._stream_named(BLOCK_FACET_KEYS).stream)
        identifiers = dict((x.identifier_raw, x)
                           for x in self.key_format.identifiers)
        for key, value in tree.iterate(self._stream_index):
            facet = CARFacet.make_from_buffer(value, name=key)
            facet.attributes = dict((identifiers[x.identifier], x.value)
                                    for x in facet.attributes_raw)
            yield facet

    def dump(self):
        """
        Pretty print version of the CAR file containing the general information
        """
        self.header.dump()
        print "\nExtended metadata: %s\n" % self.metadata.contents

        key_format = self.key_format
        print "Key Format: %s" % key_format.magic
        print "Identifier Count: %d" % key_format.num_identifiers
        for key_format in key_format.identifiers:
            print "Identifier: %s (%d)" % (key_format.identifier,
                                           key_format.identifier_raw)

        print ""

    # - Private helpers

    def _stream_index(self, index):
        block = self.blocks[index]
        self.stream.seek(block.index, 0)
        return StreamBlock(self.stream, block)

    def _stream_named(self, name):
        if name not in self.table:
            raise BOMInvalidFile("Invalid block name %s" % name)

        return StreamBlock(*self._stream_index(self.table[name]))

    def _parse(self, stream):
        fheader = self._parse_header(stream)
        self.file_header = fheader
        self.table = self._parse_table(stream)
        self.blocks = self._parse_blocks(stream)

        if fheader.magic != "BOMStore":
            raise BOMInvalidFile("Invalid magic header %s" % fheader.magic)

        if fheader.index_offset + fheader.index_size > self.size:
            raise BOMInvalidFile("Index is bigger than file")

        if fheader.table_offset + fheader.table_size > self.size:
            raise BOMInvalidFile("Table is bigger than file")

        header = self.header
        if header.magic != "RATC" or header.storage_version < 8:
            raise BOMInvalidFile("Invalid CAR file")

        # The index into the attribute list for the identifer for the matching
        # facet.
        attr = CARKeyFormatIdentifier(identifier_raw=17)
        self.identifier_index = self.key_format.identifiers.index(attr)

    def _parse_header(self, stream):
        return BOMHeader.make(stream)

    def _parse_table(self, stream):
        stream.seek(self.file_header.table_offset, 0)
        table = {}
        count, = struct.unpack(">I", stream.read(4))
        for i in xrange(count):
            index, name_len = struct.unpack(">IB", stream.read(5))
            name, = struct.unpack(">%ds" % name_len, stream.read(name_len))
            table[name] = index

        return table

    def _parse_blocks(self, stream):
        stream.seek(self.file_header.index_offset, 0)
        count, = struct.unpack(">I", stream.read(4))
        return [BOMBlock.make(stream) for i in xrange(count)]
