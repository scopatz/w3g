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

def blizdecomp(b):
    """Performs wacky blizard 'decompression' and returns bytes and len in 
    original string.
    """
    if isinstance(b, str):
        b = list(map(b2i, b))
    d = []
    pos = 0
    mask = None
    while b[pos] != 0:
        if pos%8 == 0:
            mask = b[pos]
        elif ((mask & (0x1 << (pos%8))) == 0):
            d.append(b[pos] - 1)
        else:
            d.append(b[pos])
        pos += 1
    if bytes == str:
        d = b''.join(map(chr, d))
    else:
        d = bytes(d)
    return d, pos

def blizdecode(b):
    d, l = blizdecomp(b)
    return d.decode(), l

def bits(b):
    """Returns the bits in a byte"""
    if isinstance(b, str):
        b = ord(b)
    return tuple([(b >> i) & 1 for i in range(8)])

def bitfield(b, idx):
    """Returns an integer representing the bit field. idx may be a slice."""
    f = bits(b)[idx]
    if f != 0 and f != 1:
        val = 0
        for i, x in enumerate(f):
            val += x * 2**i
        f = val
    return f

RACES = {
    0x01: 'human',
    0x02: 'orc',
    0x04: 'nightelf',
    0x08: 'undead',
    0x10: 'daemon',
    0x20: 'random',
    0x40: 'selectable/fixed',
    }
SPEED = ('slow', 'normal', 'fast', 'unused')
OBSERVER = ('off', 'unused', 'defeat', 'on')
FIXED_TEAMS = ('off', 'unused', 'unused', 'on')
GAME_TYPES = {
    0x00: 'unknown',
    0x01: '1on1',
    0x09: 'custom',
    0x1D: 'single player game',
    0x20: 'ladder team game',
    }
STATUS = {0x00: 'empty', 0x01: 'closed', 0x02: 'used'}
COLORS = ('red', 'blue', 'cyan', 'purple', 'yellow', 'orange', 'green',
          'pink', 'gray', 'light blue', 'dark green', 'brown', 'observer')
AI_STRENGTH = {0x00: 'easy', 0x01: 'normal', 0x02: 'insane'}

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

class SlotRecord(namedtuple('Player', ['player_id', 'status', 'ishuman', 'team', 
                                       'color', 'race', 'ai', 'handicap','raw', 
                                       'size'])):
    def __new__(cls, player_id=-1, status='empty', ishuman=False, team=-1, color='red', 
                race='none', ai='normal', handicap=100, raw=b'', size=0):
        self = super(SlotRecord, cls).__new__(cls, player_id=player_id, status=status, 
                                              ishuman=ishuman, team=team, color=color,
                                              race=race, ai=ai, handicap=handicap,  
                                              raw=raw, size=size)
        return self

    @classmethod
    def from_raw(cls, data):
        kw = {'player_id': b2i(data[0]), 
              'status': STATUS[b2i(data[2])],
              'ishuman': (b2i(data[3]) == 0x00),
              'team': b2i(data[4]),
              'color': COLORS[b2i(data[5])],
              'race': RACES.get(b2i(data[6]), 'none'),
              }
        kw['size'] = size = len(data)
        kw['raw'] = data
        if 8 <= size:
            kw['ai'] = AI_STRENGTH[b2i(data[7])]
        if 9 <= size:
            kw['handicap'] = b2i(data[8])
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
        # perform wacky decompression
        decomp, i = blizdecomp(data[offset:])
        offset += i + 1
        # get game settings
        settings = decomp[:13]
        self.game_speed = SPEED[bitfield(settings[0], slice(2))]
        vis = bits(settings[1])
        self.visibility_hide_terrain = bool(vis[0])
        self.visibility_map_explored = bool(vis[1])
        self.visibility_always_visible = bool(vis[2])
        self.visibility_default = bool(vis[3])
        self.observer = OBSERVER[vis[4] + 2 * vis[5]]
        self.teams_together = bool(vis[6])
        self.fixed_teams = FIXED_TEAMS[bitfield(settings[2], slice(1, 3))]
        ctl = bits(settings[3])
        self.full_shared_unit_control = bool(ctl[0])
        self.random_hero = bool(ctl[1])
        self.random_races = bool(ctl[2])
        self.observer_referees = bool(ctl[6])
        self.map_name, i = nulltermstr(decomp[13:])
        self.creator_name, _ = nulltermstr(decomp[13+i+1:])
        # back to less dense data
        self.player_count = b2i(data[offset:offset+4])
        offset += 4
        self.game_type = GAME_TYPES[b2i(data[offset])]
        offset += 1
        priv = b2i(data[offset])
        offset += 1
        self.ispublic = (priv == 0x00)
        self.isprivate = (priv == 0x08)
        offset += WORD  # more buffer space
        self.language_id = data[offset:offset+4]
        offset += 4
        while b2i(data[offset]) == 0x16:
            self.players.append(Player.from_raw(data[offset:]))
            offset += self.players[-1].size
            offset += 4  # 4 unknown padding bytes after each player record
        assert b2i(data[offset]) == 0x19
        offset += 1  # skip RecordID
        nstartbytes = b2i(data[offset:offset+WORD])
        offset += WORD
        nrecs = b2i(data[offset])
        offset += 1
        recsize = int((nstartbytes - DWORD - 3) / nrecs)
        assert 7 <= recsize <= 9
        rawrecs = data[offset:offset+(recsize*nrecs)]
        offset += recsize*nrecs
        self.slot_records = [SlotRecord.from_raw(rawrecs[n*recsize:(n+1)*recsize]) \
                             for n in range(nrecs)]
        print(self.slot_records)
        self.random_seed = data[offset:offset+DWORD]
        offset += DWORD

if __name__ == '__main__':
    f = File(sys.argv[1])

