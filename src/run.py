import argparse

from car import CARFile
from decoders import RenditionDecoder


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filepath", help="Full path of the file to be parsed")
    parser.add_argument("-s", help="Dump CAR information", dest="show",
                        action='store_true')
    parser.add_argument("-o", help="Dump all images into the given directory",
                        dest="directory")
    arguments = parser.parse_args()

    content = CARFile(arguments.filepath)
    if arguments.show:
        content.dump()
        for facet in content.facets:
            facet.dump()

        for rendition in content.renditions:
            rendition.dump()

    if arguments.directory:
        for rendition in content.renditions:
            decoder = RenditionDecoder(rendition)
            decoder.decode()


if __name__ == "__main__":
    main()
