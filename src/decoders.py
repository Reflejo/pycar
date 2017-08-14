class RenditionDecoderError(Exception):
    pass


class RenditionDecoder(object):

    def __init__(self, rendition):
        self.rendition = rendition

    def decode(self):
        raw = self.rendition.raw
        if not raw:
            print self.rendition
            return

        if self.rendition.magic != "CTSI":
            raise RenditionDecoderError("Invalid magic header %s (%s)" %
                                        (raw.magic, self.rendition.magic))

        # TODO
