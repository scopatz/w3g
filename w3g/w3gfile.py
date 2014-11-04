"""Implements the basic w3g file class. Based on information available at 

* http://w3g.deepnode.de/files/w3g_format.txt
"""
from __future__ import unicode_literals, print_function
import io
import sys

WORD = 2   # bytes
DWORD = 4  # bytes, double word

if sys.version_info[0] < 3:
    import struct
    b2i = lambda b: struct.unpack('<' + ('L' if len(b) == DWORD else 'H'), b)[0]
else:
    b2i = lambda b: int.from_bytes(b, 'little')

class File(object):
    """A class that represents w3g files.

    Attributes
    ----------
    replay_length : game play time in ms
    """

    def __init__(self, f):
        """Parameters
        ----------
        f : file handle or str of path name
        """
        # init
        opened_here = False
        if isinstance(f, str):
            opened_here = True
            f = io.open(f, 'rb')
        self.f = f
        self.loc = 0

        # read in
        self._read_header()

        # clean up 
        if opened_here:
            f.close()

    def __del__(self):
        if not self.f.closed:
            self.f.close()

    @property
    def loc(self):
        return self.f.tell()

    @loc.setter
    def loc(self, value):
        self.f.seek(value)

    def _read_header(self):
        f = self.f
        self.loc = 28
        self.header_size = b2i(f.read(DWORD))
        print(self.header_size)
        self.file_size_compressed = b2i(f.read(DWORD))
        self.header_version = hv = b2i(f.read(DWORD))
        self.file_size_decompressed = b2i(f.read(DWORD))
        self.nblocks = b2i(f.read(DWORD))
        self.loc = 0x30
        if hv == 0:
            self.loc += WORD
            self.version_num = b2i(f.read(WORD))
        elif hv == 1:
            self.version_id_str = f.read(DWORD)[::-1].decode()
            self.version_num = b2i(f.read(DWORD))
        else:
            raise ValueError("Header must be either v0 or v1, got v{0}".format(hv))
        self.build_num = b2i(f.read(WORD))
        self.flags = f.read(WORD)
        iflags = b2i(self.flags)
        self.singleplayer = (iflags == 0)
        self.multiplayer = (iflags == 0x8000)
        self.replay_length = b2i(f.read(DWORD))
        self.header_checksum = b2i(f.read(DWORD))

if __name__ == '__main__':
    import sys
    print("opening", sys.argv[1])
    f = File(sys.argv[1])

