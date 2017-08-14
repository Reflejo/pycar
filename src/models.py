import cStringIO as StringIO
import struct

from utils import cached_property
from parse import CAR_ATTRIBUTE_BY_ID, CAR_RENDITION_LAYOUT_BY_ID, Parse


class CARParsingError(Exception):
    pass


class Model(object):

    custom = []

    def __init__(self, **kwargs):
        for field, _ in self.__class__.fields:
            setattr(self, field, kwargs.get(field))

    @classmethod
    def make(cls, stream, **kwargs):
        instance = cls()
        for field, unpack in cls.fields:
            setattr(instance, field, unpack(instance, stream))

        for key, value in kwargs.iteritems():
            setattr(instance, key, value)

        return instance

    @classmethod
    def make_from_buffer(cls, buffer, **kwargs):
        stream = StringIO.StringIO(buffer)
        return cls.make(stream, **kwargs)

    def __repr__(self):
        return repr(str(self))

    def __str__(self):
        cls = self.__class__
        attrs = ["%s=%s" % (field, getattr(self, field))
                 for field, _ in cls.fields if field != "reserved"]
        attrs += ["%s=%s" % (field, getattr(self, field))
                  for field in cls.custom]
        return "<%s %s>" % (cls.__name__, ", ".join(attrs))


class CARHeader(Model):
    def _uuid(self, stream):
        content, = struct.unpack("<16s", stream.read(16))
        return content.encode("hex")

    fields = [
        ('magic', Parse.fixed(">4s")),
        ('ui_version', Parse.fixed("<I")),
        ('storage_version', Parse.fixed("<I")),
        ('storage_timestamp', Parse.fixed("<I")),
        ('rendition_count', Parse.fixed("<I")),
        ('file_creator', Parse.terminated("\n", fixed=128)),
        ('other_creator', Parse.terminated("\x00", fixed=256)),
        ('uuid', _uuid),
        ('associated_checksum', Parse.fixed("<I")),
        ('schema_version', Parse.fixed("<I")),
        ('color_space_id', Parse.fixed("<I")),
        ('key_semantics', Parse.fixed("<I")),
    ]

    def dump(self):
        print "Magic: %s" % self.magic
        print "UI version: %x" % self.ui_version
        print "Storage version: %x" % self.storage_version
        print "Storage Timestamp: %d" % self.storage_timestamp
        print "Rendition Count: %x" % self.rendition_count
        print "Creator: %s" % self.file_creator
        print "Other Creator: %s" % self.other_creator
        print "UUID: %s" % self.uuid
        print "Associated Checksum: %x" % self.associated_checksum
        print "Schema Version: %d" % self.schema_version
        print "Color space ID: %d" % self.color_space_id
        print "Key Semantics: %d" % self.key_semantics


class CARKeyFormatIdentifier(Model):
    fields = [
        ('identifier_raw', Parse.fixed("<I")),
    ]

    def __eq__(self, other):
        return self.identifier_raw == other.identifier_raw

    @property
    def identifier(self):
        return CAR_ATTRIBUTE_BY_ID.get(self.identifier_raw, "unknown")


class CARKeyFormat(Model):
    fields = [
        ('magic', Parse.fixed(">4s")),
        ('reserved', Parse.fixed("<I")),
        ('num_identifiers', Parse.fixed("<I")),
        ('identifiers', Parse.array(model=CARKeyFormatIdentifier,
                                    count="num_identifiers")),
    ]


class CARRenditionFlag(Model):
    fields = [
        ('flags', Parse.fixed("<B")),
        ('reserved', Parse.fixed("<3s")),
    ]


class CARRenditionMetadata(Model):
    fields = [
        ('modification_date', Parse.fixed("<I")),
        ('layout_raw', Parse.fixed("<H")),
        ('reserved', Parse.fixed("<H")),
        ('name', Parse.terminated("\x00", fixed=128)),
    ]


class CARRenditionSlice(Model):
    fields = [
        ('x', Parse.fixed("<I")),
        ('y', Parse.fixed("<I")),
        ('width', Parse.fixed("<I")),
        ('height', Parse.fixed("<I")),
    ]


class CARRenditionMetric(Model):
    fields = [
        ('width', Parse.fixed("<I")),
        ('height', Parse.fixed("<I")),
    ]


class CARRenditionComposition(Model):
    fields = [
        ('blend_mode', Parse.fixed("<I")),
        ('opacity', Parse.fixed("<f")),
    ]


class CARRenditionUTI(Model):
    fields = [
        ('length', Parse.fixed("<I")),
        ('uti', Parse.fixed("<1s")),
    ]


class CARRenditionBitmapInfo(Model):
    fields = [
        ('exif_orientation', Parse.fixed("<I")),
    ]


class CARRenditionBytesPerRow(Model):
    fields = [
        ('bytes_per_row', Parse.fixed("<I")),
    ]


class CARRenditionReference(Model):
    fields = [
        ('magic', Parse.fixed("<4s")),
        ('padding', Parse.fixed("<I")),
        ('x', Parse.fixed("<I")),
        ('y', Parse.fixed("<I")),
        ('width', Parse.fixed("<I")),
        ('height', Parse.fixed("<I")),
        ('layout', Parse.fixed("<H")),
        ('key_length', Parse.fixed("<H")),
    ]


class CARRenditionInfo(Model):
    fields = [
        ('magic', Parse.fixed("<I")),
        ('length', Parse.fixed("<I")),
        ('content', Parse.dynamic("length")),
    ]

    @cached_property
    def parsed(self):
        content = StringIO.StringIO(self.content)
        make_map = {
            1001: Parse.array_dynamic(model=CARRenditionSlice),
            1003: Parse.array_dynamic(model=CARRenditionMetric),
            1004: Parse.model(CARRenditionComposition),
            1005: Parse.model(CARRenditionUTI),
            1006: Parse.model(CARRenditionBitmapInfo),
            1007: Parse.model(CARRenditionBytesPerRow),
            1010: Parse.model(CARRenditionReference),
        }
        content_make = make_map.get(self.magic)
        return content_make(self, content) if content_make else None

    def __str__(self):
        return "<CARRenditionInfo magic=%s, length=%s, parsed=%s>" % \
            (self.magic, self.length, self.parsed)


class CARFacetAttribute(Model):
    fields = [
        ('identifier', Parse.fixed("<H")),
        ('value', Parse.fixed("<H")),
    ]


class CARFacet(Model):
    custom = ['name']
    fields = [
        ('x', Parse.fixed("<H")),
        ('y', Parse.fixed("<H")),
        ('attributes_count', Parse.fixed("<H")),
        ('attributes_raw', Parse.array(model=CARFacetAttribute,
                                       count="attributes_count")),
    ]

    def dump(self):
        print "Facet: %s" % self.name
        for attribute, value in self.attributes.iteritems():
            print "[%.2d] %s = %s" % \
                (attribute.identifier_raw, attribute.identifier, value)


class CARRenditionRaw(Model):
    fields = [
        ('magic', Parse.fixed("<4s")),
        ('reserved', Parse.fixed("<I")),
        ('length', Parse.fixed("<I")),
        ('binary', Parse.dynamic("length")),
    ]


class CARRendition(Model):
    RESIZE_MODE_FIXED = "Fixed Size"
    RESIZE_MODE_TILE = "Tile"
    RESIZE_MODE_SCALE = "Scale"
    RESIZE_MODE_HUNIFORM_VSCALE = "Horizontal Uniform; Vertical Scale"
    RESIZE_MODE_HSCALE_VUNIFORM = "Horizontal Scale; Vertical Uniform"

    @classmethod
    def make_from_buffer(cls, buffer, **kwargs):
        stream = StringIO.StringIO(buffer)
        return cls.make(stream, **kwargs)

    fields = [
        ('magic', Parse.fixed("<4s")),
        ('version', Parse.fixed("<I")),
        ('flags', Parse.model(CARRenditionFlag)),
        ('width', Parse.fixed("<I")),
        ('height', Parse.fixed("<I")),
        ('scale_factor', Parse.fixed("<I")),
        ('pixel_format', Parse.fixed("<4s")),
        ('color_space_id', Parse.fixed("<B")),
        ('reserved', Parse.fixed("<3s")),
        ('modification_date', Parse.fixed("<I")),
        ('layout_raw', Parse.fixed("<H")),
        ('reserved', Parse.fixed("<H")),
        ('name', Parse.terminated("\x00", fixed=128)),
        ('info_len', Parse.fixed("<I")),
        ('bitmap_count', Parse.fixed("<I")),
        ('reserved', Parse.fixed("<I")),
        ('payload_size', Parse.fixed("<I")),
        ('info', Parse.array_fixed(model=CARRenditionInfo, size='info_len')),
        ('content', Parse.dynamic("payload_size")),
    ]

    @cached_property
    def raw(self):
        if len(self.content):
            return CARRenditionRaw.make_from_buffer(self.content)

    @cached_property
    def layout(self):
        return CAR_RENDITION_LAYOUT_BY_ID.get(self.layout_raw, "unknown")

    @cached_property
    def is_resizable(self):
        return 25 >= self.layout_raw >= 20 and len(self.slices) > 1

    @cached_property
    def slices(self):
        return filter(lambda x: x.parsed is CARRenditionSlice, self.info)

    @cached_property
    def resize_mode(self):
        mode_map = {
            "one_part_tile": CARRendition.RESIZE_MODE_TILE,
            "three_part_horizontal_tile": CARRendition.RESIZE_MODE_TILE,
            "three_part_vertical_tile": CARRendition.RESIZE_MODE_TILE,
            "nine_part_tile": CARRendition.RESIZE_MODE_TILE,
            "one_part_scale": CARRendition.RESIZE_MODE_SCALE,
            "three_part_horizontal_scale": CARRendition.RESIZE_MODE_SCALE,
            "three_part_vertical_scale": CARRendition.RESIZE_MODE_SCALE,
            "nine_part_scale": CARRendition.RESIZE_MODE_SCALE,
            "nine_part_horizontal_uniform_vertical_scale":
                CARRendition.RESIZE_MODE_HUNIFORM_VSCALE,
            "nine_part_horizontal_uniform_vertical_scale":
                CARRendition.RESIZE_MODE_HSCALE_VUNIFORM,
        }
        return mode_map.get(self.layout, CARRendition.RESIZE_MODE_FIXED)

    def dump(self):
        print "Rendition: %s" % self.name
        print "Width: %d" % self.width
        print "Height: %d" % self.height
        print "Scale: %f" % (self.scale_factor / 100.0)
        print "Layout: %s" % self.layout_raw
        print "Resizable: %d" % self.is_resizable
        print "Payload size: %d" % self.payload_size
        if self.is_resizable:
            for i, slice in enumerate(self.slices):
                print "Slice %d: (%u, %u) %u x %u" % \
                    (i, slice.x, slice.y, slice.width, slice.height)

        print "Resize mode: %s" % self.resize_mode
        print "Attributes:"
        for attribute, value in self.attributes.iteritems():
            print "[%.2d] %s = %s" % \
                (attribute.identifier_raw, attribute.identifier, value)

        print ""
