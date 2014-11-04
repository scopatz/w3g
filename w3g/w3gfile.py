"""Implements the basic w3g file class. Based on information available at 

* http://w3g.deepnode.de/files/w3g_format.txt
"""
from __future__ import unicode_literals, print_function
import io
import sys
import base64
import zlib
from collections import namedtuple

WORD = 2   # bytes
DWORD = 4  # bytes, double word
NULL = b'\0'

if sys.version_info[0] < 3:
    import struct
    BLENFLAG = {1: 'B', WORD: 'H', DWORD: 'L'}
    b2i = lambda b: struct.unpack('<' + BLENFLAG[len(b)], b)[0]
else:
    b2i = lambda b: b if isinstance(b, int) else int.from_bytes(b, 'little')

def nulltermstr(b):
    """Returns the next null terminated string from bytes and its length."""
    i = b.find(NULL)
    s = b[:i].decode('utf-8')
    return s, i

def blizdecode(b):
    pass

RACES = {
    0x01: 'human',
    0x02: 'orc',
    0x04: 'nightelf',
    0x08: 'undead',
    0x10: 'daemon',
    0x20: 'random',
    0x40: 'selectable/fixed',
    }

class Player(namedtuple('Player', ['id', 'name', 'race', 'ishost', 
                                   'runtime', 'raw', 'size'])):
    def __new__(cls, id=-1, name='', race='', ishost=False, runtime=-1, 
                 raw=b'', size=0):
        self = super(Player, cls).__new__(cls, id=id, name=name, race=race, 
                                          ishost=ishost, runtime=runtime, raw=raw, 
                                          size=size)
        return self

    @classmethod
    def from_raw(cls, data):
        kw = {'ishost': b2i(data[0]) == 0, 
              'id': b2i(data[1])}
        kw['name'], i = nulltermstr(data[2:])
        n = 2 + i + 1
        custom_or_ladder = b2i(data[n])
        n += 1
        if custom_or_ladder == 0x01:  # custom
            n += 1
            kw['runtime'] = 0
            kw['race'] = 'none'
        elif custom_or_ladder == 0x08:  # ladder
            kw['runtime'] = b2i(data[n:n+4])
            n += 4
            race_flag = b2i(data[n:n+4])
            n += 4
            kw['race'] = RACES[race_flag]
        else:
            raise ValueError("Player not recognized custom or ladder.")
        kw['size'] = n
        kw['raw'] = data[:n]
        return cls(**kw)

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
        self.have_startup = False

        # read in
        self._read_header()
        self._read_blocks()

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

    def _read_blocks(self):
        f = self.f
        self.loc = self.header_size
        block_size = b2i(f.read(WORD))
        block_size_decomp = b2i(f.read(WORD))
        self.loc += DWORD
        raw = f.read(block_size)
        data = zlib.decompress(raw)
        if len(data) != block_size_decomp:
            raise zlib.error("Decompressed data size does not match expected size.")
        if not self.have_startup:
            self._parse_startup(data)
            self.have_startup = True

    def _parse_startup(self, data):
        offset = 4  # first four bytes have unknown meaning
        self.players = [Player.from_raw(data[offset:])]
        offset += self.players[0].size
        self.game_name, i = nulltermstr(data[offset:])
        offset += i + 1
        offset += 1  # extra null byte after game name
        print(self.game_name)
        

if __name__ == '__main__':
    f = File(sys.argv[1])

