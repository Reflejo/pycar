from models import Model
from parse import Parse


class BOMInvalidTreeType(Exception):
    pass


class BOMHeader(Model):
    fields = [
        ('magic', Parse.fixed(">8s")),
        ('version', Parse.fixed(">I")),
        ('block_count', Parse.fixed(">I")),
        ('index_offset', Parse.fixed(">I")),
        ('index_size', Parse.fixed(">I")),
        ('table_offset', Parse.fixed(">I")),
        ('table_size', Parse.fixed(">I")),
    ]


class BOMBlock(Model):
    fields = [
        ('index', Parse.fixed(">I")),
        ('size', Parse.fixed(">I")),
    ]


class BOMPathIndex(Model):
    fields = [
        ('value_index', Parse.fixed(">I")),
        ('key_index', Parse.fixed(">I")),
    ]


class BOMPath(Model):
    fields = [
        ('is_leaf', Parse.fixed(">H")),
        ('count', Parse.fixed(">H")),
        ('forward', Parse.fixed(">I")),
        ('backwards', Parse.fixed(">I")),
        ('indexes', Parse.array(model=BOMPathIndex, count="count")),
    ]


class BOMTree(Model):
    def iterate(self, stream_index):
        if self.magic != "tree" or self.version != 1:
            raise BOMInvalidTreeType("Invalid tree type %s" % self)

        path = BOMPath.make(stream_index(self.child).stream)
        if not path.is_leaf:
            index = path.indexes[0]
            path = BOMPath.make(stream_index(index.value_index).stream)

        while path:
            for index in path.indexes:
                stream, block = stream_index(index.key_index)
                key = stream.read(block.size)
                stream, block = stream_index(index.value_index)
                value = stream.read(block.size)
                yield key, value

            if not path.forward:
                break

            path = BOMPath.make(stream_index(path.forward).stream)

    custom = ["name"]
    fields = [
        ('magic', Parse.fixed(">4s")),
        ('version', Parse.fixed(">I")),
        ('child', Parse.fixed(">I")),
        ('block_size', Parse.fixed(">I")),
        ('path_count', Parse.fixed(">I")),
        ('unknown', Parse.fixed(">b")),
    ]


class BOMExtendedMetadata(Model):
    fields = [
        ('magic', Parse.fixed(">4s")),
        ('contents', Parse.terminated("\x00", fixed=768)),
        ('creator', Parse.terminated("\n", fixed=256)),
    ]
