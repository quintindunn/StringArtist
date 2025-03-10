import logging
import sys

from StringArtist.gui import GUI


def main():
    gui = GUI()
    gui.main_loop()


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    main()
