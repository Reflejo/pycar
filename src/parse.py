import struct

CAR_ATTRIBUTE_BY_ID = {
    1: "element",
    2: "part",
    3: "size",
    4: "direction",
    6: "value",
    8: "dimension1",
    9: "dimension2",
    10: "state",
    11: "layer",
    12: "scale",
    14: "presentation_state",
    15: "idiom",
    16: "subtype",
    17: "identifier",
    18: "previous_value",
    19: "previous_state",
    20: "size_class_horizontal",
    21: "size_class_vertical",
    22: "memory_class",
    23: "graphics_class",
    24: "display_gamut",
    25: "deployment_target",
}

CAR_RENDITION_LAYOUT_BY_ID = {
    6: "gradient",
    7: "effect",
    10: "one_part_fixed_size",
    11: "one_part_tile",
    12: "one_part_scale",
    20: "three_part_horizontal_tile",
    21: "three_part_horizontal_scale",
    22: "three_part_horizontal_uniform",
    23: "three_part_vertical_tile",
    24: "three_part_vertical_scale",
    25: "three_part_vertical_uniform",
    30: "nine_part_tile",
    31: "nine_part_scale",
    32: "nine_part_horizontal_uniform_vertical_scale",
    33: "nine_part_horizontal_scale_vertical_uniform",
    34: "nine_part_edges_only",
    40: "six_part",
    50: "animation_filmstrip",

    # Non-images > 999:
    1000: "raw_data",
    1001: "external_link",
    1002: "layer_stack",
    1003: "internal_link",
    1004: "asset_pack",
}


class Parse(object):
    sizes = {"I": 4, "?": 1, "b": 1, "B": 1, "H": 2, "f": 4}

    @classmethod
    def fixed(cls, size_identifier):
        def parse(instance, stream):
            if len(size_identifier) > 2:
                size = int(size_identifier[1:-1])
                identifier = size_identifier[-1]
            else:
                size = cls.sizes[size_identifier[1:]]

            content, = struct.unpack(size_identifier, stream.read(size))
            reverse = size_identifier[0] == "<" and size_identifier[-1] == "s"
            return content[::-1] if reverse else content

        return parse

    @classmethod
    def dynamic(cls, size_field):
        def parse(instance, stream):
            size = int(getattr(instance, size_field))
            return struct.unpack("<%ds" % size, stream.read(size))[0]

        return parse

    @classmethod
    def model(cls, model):
        def parse(instance, stream):
            return model.make(stream)

        return parse

    @classmethod
    def array_fixed(cls, model, size):
        def parse(instance, stream):
            total_size = size
            if size and not isinstance(size, int):
                total_size = int(getattr(instance, size))

            start = stream.tell()
            content = []
            while stream.tell() - start < total_size:
                content.append(model.make(stream))

            return content

        return parse

    @classmethod
    def array(cls, model, count):
        def parse(instance, stream):
            elements_count = count
            if count and not isinstance(count, int):
                elements_count = int(getattr(instance, count))

            return [model.make(stream) for _ in xrange(elements_count)]

        return parse

    @classmethod
    def array_dynamic(cls, model):
        def parse(instance, stream):
            elements_count, = struct.unpack("<I", stream.read(4))
            return [model.make(stream) for _ in xrange(elements_count)]

        return parse

    @classmethod
    def terminated(cls, terminator, fixed=0):
        def parse(instance, stream):
            parsed = ""
            while True:
                char = stream.read(1)
                if char == terminator:
                    break

                parsed += char

            if fixed - len(parsed) > 0:
                stream.read(fixed - len(parsed) - 1)

            return parsed

        return parse
