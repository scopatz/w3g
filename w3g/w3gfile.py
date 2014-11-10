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

# build number associated with v1.07 of the game
BUILD_1_07 = 6031

# build number associated with v1.13 of the game
BUILD_1_13 = 6037

if sys.version_info[0] < 3:
    import struct
    BLENFLAG = {1: 'B', WORD: 'H', DWORD: 'L'}
    b2i = lambda b: struct.unpack('<' + BLENFLAG[len(b)], b)[0]

    # to print unicode
    import codecs
    UTF8Writer = codecs.getwriter('utf8')
    sys.stdout = UTF8Writer(sys.stdout)
    def umake(f):
        def uprint(*objects, **kw):
            uo = map(unicode, objects)
            f(*uo, **kw)
        return uprint
    print = umake(print)

    # fake lru_cache
    lru_cache = lambda maxsize=128, typed=False: lambda f: f
else:
    b2i = lambda b: b if isinstance(b, int) else int.from_bytes(b, 'little')
    from functools import lru_cache

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
SPEEDS = ('slow', 'normal', 'fast', 'unused')
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
SELECT_MODES = {
    0x00: 'team & race selectable',
    0x01: 'team not selectable',
    0x03: 'team & race not selectable',
    0x04: 'race fixed to random',
    0xcc: 'automated match making',
    }
CHAT_MODES = {0x00: 'all', 0x01: 'allies', 0x02: 'observers'}
NUMERIC_ITEM = b'\r\x00'
ITEMS = {
    # string encoded item id
    b'AEah': 'Thorns Aura',
    b'AEar': 'Trueshot',
    b'AEbl': 'Blink',
    b'AEer': 'Entangling Roots',
    b'AEev': 'Evasion',
    b'AEfk': 'Fan of Knives',
    b'AEfn': 'Force of Nature',
    b'AEim': 'Immolation',
    b'AEmb': 'Mana Burn',
    b'AEme': 'Metamorphosis',
    b'AEsf': 'Starfall',
    b'AEsh': 'Shadow Strike',
    b'AEst': 'Scout',
    b'AEsv': 'Vengence',
    b'AEtq': 'Tranquility',
    b'AHab': 'Brilliance Aura',
    b'AHad': 'Devotion Aura',
    b'AHav': 'Avatar',
    b'AHbh': 'Bash',
    b'AHbn': 'Banish',
    b'AHbz': 'Blizzard',
    b'AHdr': 'Siphon Mana',
    b'AHds': 'Divine Shield',
    b'AHfa': 'Searing Arrows',
    b'AHfs': 'Flame Strike',
    b'AHhb': 'Holy Bolt',
    b'AHmt': 'Mass Teleport',
    b'AHpx': 'Summon Phoenix',
    b'AHre': 'Resurrection',
    b'AHtb': 'Storm Bolt',
    b'AHtc': 'Thunder Clap',
    b'AHwe': 'Summon Water Elemental',
    b'AOae': 'Endurance Aura',
    b'AOcl': 'Chain Lightning',
    b'AOcr': 'Critical Strike',
    b'AOeq': 'Earthquake',
    b'AOfs': 'Far Sight',
    b'AOhw': 'Healing Wave',
    b'AOhx': 'Hex',
    b'AOmi': 'Mirror Image',
    b'AOre': 'Reincarnation',
    b'AOsf': 'Feral Spirit',
    b'AOsh': 'Shockwave',
    b'AOsw': 'Serpent Ward',
    b'AOvd': 'Big Bad Voodoo',
    b'AOwk': 'Wind Walk',
    b'AOws': 'War Stomp',
    b'AOww': 'Blade Storm',
    b'AUan': 'Animate Dead',
    b'AUau': 'Unholy Aura',
    b'AUav': 'Vampiric Aura',
    b'AUcb': 'Carrion Beetles',
    b'AUcs': 'Carrion Swarm',
    b'AUdc': 'Death Coil',
    b'AUdd': 'Death and Decay',
    b'AUdp': 'Death Pact',
    b'AUdr': 'Dark Ritual',
    b'AUfn': 'Frost Nova',
    b'AUfu': 'Frost Armor',
    b'AUim': 'Impale',
    b'AUin': 'Inferno',
    b'AUls': 'Locust Swarm',
    b'AUsl': 'Sleep',
    b'AUts': 'Spiked Carapace',
    b'eaoe': 'Ancient of Lore',
    b'eaom': 'Ancient of War',
    b'eaow': 'Ancient of Wind',
    b'earc': 'Archer',
    b'eate': 'Altar of Elders',
    b'ebal': 'Ballista',
    b'Ecen': 'Cenarius',
    b'echm': 'Chimeara',
    b'edcm': 'Druid of the Claw (Metamophed)',
    b'Edem': 'Demon Hunter',
    b'eden': 'Ancient of Wonders',
    b'Edmm': 'Demon Hunter (Metamophed)',
    b'edob': 'Hunter\'s Hall',
    b'edoc': 'Druid of the Claw',
    b'edol': 'Bear Den',
    b'edos': 'Chimaera Roost',
    b'edot': 'Druid of the Talon',
    b'edry': 'Dryad',
    b'edtm': 'Druid of the Talon (Metamophed)',
    b'Eevi': 'Illidan',
    b'Eevm': 'Illidan Demon',
    b'efdr': 'Faerie Dragon',
    b'efon': 'Ent',
    b'egol': 'Entangled Gold Mine',
    b'ehip': 'Hippogryph',
    b'ehpr': 'Hippogryph Rider',
    b'Ekee': 'Keeper of the Grove',
    b'Emoo': 'Priestess of the Moon',
    b'emow': 'Moon Well',
    b'emtg': 'Mountain Giant',
    b'esen': 'Huntress',
    b'eshd': 'Shandris',
    b'etoa': 'Tree of Ages',
    b'etoe': 'Tree of Eternity',
    b'etol': 'Tree of Life',
    b'etrp': 'Ancient Protector',
    b'Ewar': 'Warden',
    b'Ewrd': 'Maiev',
    b'ewsp': 'Wisp',
    b'halt': 'Altar of Kings',
    b'Hamg': 'Archmage',
    b'harm': 'Workshop',
    b'hars': 'Arcane Sanctum',
    b'hatw': 'Arcane Tower',
    b'hbar': 'Barracks',
    b'hbep': 'Blood Elf Priest',
    b'hbes': 'Blood Elf Sorceress',
    b'hbla': 'Blacksmith',
    b'Hblm': 'Blood Mage',
    b'hcas': 'Castle',
    b'hcth': 'High Elf Footman',
    b'hctw': 'Cannon Tower',
    b'hdhw': 'Dragonhawk Rider',
    b'hfoo': 'Footman',
    b'hgra': 'Aviary',
    b'hgry': 'Gryphon Rider',
    b'hgtw': 'Guard Tower',
    b'hgyr': 'Flying Machine',
    b'hhes': 'High Elf Swordman',
    b'hhou': 'House',
    b'Hjai': 'Jaina',
    b'Hkal': 'Kael\'thas',
    b'hkee': 'Keep',
    b'hkni': 'Knight',
    b'Hlgr': 'Garithos',
    b'hlum': 'Lumber Mill',
    b'Hmbr': 'Muradin',
    b'hmil': 'Militia',
    b'Hmkg': 'Mountain King',
    b'hmpr': 'Priest',
    b'hmtm': 'Mortar',
    b'hmtt': 'Siege Engine',
    b'Hpal': 'Paladin',
    b'hpea': 'Peasant',
    b'hrif': 'Rifleman',
    b'hrtt': 'Siege Engine (Rocket)',
    b'hsor': 'Sorceress',
    b'hspt': 'Spell Breaker',
    b'htow': 'Town Hall',
    b'htws': 'Church',
    b'hvlt': 'Arcane Vault',
    b'Hvsh': 'Lady Vashj',
    b'Hvwd': 'Sylvanus',
    b'hwat': 'Elemental',
    b'hwtw': 'Watch Tower',
    b'nbal': 'Doomgaurd',
    b'Nbbc': 'Chaos Blademaster',
    b'ncap': 'Corrupt Protector',
    b'ncaw': 'Corrup Ancient of War',
    b'nchg': 'Chaos Grunt',
    b'nchr': 'Chaos Raider',
    b'nchw': 'Chaos Warlock',
    b'nckb': 'Chaos Kodo Beast',
    b'ncmw': 'Corrupt Moon Well',
    b'ncpn': 'Chaos Peon',
    b'nctl': 'Corrupt Tree of Life',
    b'ndmg': 'Demon Gate',
    b'nefm': 'High Elf Farm',
    b'negf': 'High Elf Earth',
    b'negm': 'High Elf Sky',
    b'negt': 'High Elf Guard Tower',
    b'negt': 'High Elf Tower',
    b'nenc': 'Corrupt Treant',
    b'nenp': 'Poison Treant',
    b'nepl': 'Plauge Treant',
    b'nfel': 'Felhound',
    b'nfrb': 'Furbolg Tracker',
    b'nfre': 'Furbolg Elder',
    b'nfrg': 'Furbolg Champion',
    b'nfrl': 'Furbolg',
    b'nfrs': 'Furbolg Shaman',
    b'ngsp': 'Sapper',
    b'nhea': 'High Elf Archer',
    b'nheb': 'High Elf Barracks',
    b'nhew': 'Blood Elf Peasant',
    b'nhyc': 'Dragon Turtle',
    b'ninf': 'Infernal',
    b'nmpe': 'Mur\'gul Slave',
    b'nmyr': 'Myrmidon',
    b'nnad': 'Altar of the Depths',
    b'nnfm': 'Coral Bed',
    b'Nngs': 'Naga Sorceress',
    b'nnmg': 'Mur\'gul Reaver',
    b'nnrg': 'Naga Royal Guard',
    b'nnsa': 'Shrine of Azshara',
    b'nnsg': 'Naga Spawning Grounds',
    b'nnsw': 'Naga Siren',
    b'nntg': 'Tidal Guardian',
    b'nntt': 'Temple of Tides',
    b'nomg': 'Ogre Magi',
    b'npgf': 'Pig Farm',
    b'Npld': 'Pit Lord',
    b'nrwm': 'Orc Dragonrider',
    b'nsat': 'Trickster',
    b'nska': 'Skeleton Archer',
    b'nskf': 'Burning Archer',
    b'nskg': 'Giant Skeleton Warrior',
    b'nskm': 'Skeletal Marksman',
    b'nsnp': 'Snap Dragon',
    b'nsth': 'Hellcaller',
    b'nstl': 'Soulstealer',
    b'nsts': 'Shadowdancer',
    b'nsty': 'Satyr',
    b'nw2w': 'Warcraft II Warlock',
    b'nwgs': 'Couatl',
    b'nws1': 'Dragon Hawk',
    b'nzep': 'Zepplin',
    b'oalt': 'Altar of Storms',
    b'oang': 'Guardian',
    b'obar': 'Orc Barracks',
    b'obea': 'Beastiary',
    b'Obla': 'Blademaster',
    b'ocat': 'Catapult',
    b'ocbw': 'Chaos Burrow',
    b'odoc': 'Troll Witch Doctor',
    b'Ofar': 'Far Seer',
    b'ofor': 'Forge',
    b'ofrt': 'Fortress',
    b'ogre': 'Great Hall',
    b'Ogrh': 'Grom Hellscream',
    b'ogru': 'Grunt',
    b'ohun': 'Troll Headhunter',
    b'okod': 'Kodo Beast',
    b'opeo': 'Peon',
    b'Opgh': 'Chaos Grom Hellscream',
    b'orai': 'Raider',
    b'Oshd': 'Shadow Hunter',
    b'oshm': 'Shaman',
    b'osld': 'Spirit Lodge',
    b'ospm': 'Spirit Walker (Metamophed)',
    b'ospw': 'Spirit Walker',
    b'ostr': 'Stronghold',
    b'otau': 'Tauren',
    b'otbk': 'Troll Berserker',
    b'otbr': 'Troll Batrider',
    b'Otch': 'Tauren Chieftain',
    b'Othr': 'Thrall',
    b'otrb': 'Burrow',
    b'otto': 'Tauren Totem',
    b'ovln': 'Voodoo Lounge',
    b'owtw': 'Orc Watch Tower',
    b'owyv': 'Wyvern',
    b'Recb': 'Upgrade Corrosive Breath',
    b'Redc': 'Upgrade Druid of the Claw',
    b'Redt': 'Upgrade Druid of the Talon',
    b'Reeb': 'Upgrade Mark of the Claw',
    b'Reec': 'Upgrade Mark of the Talon',
    b'Rehs': 'Upgrade Hardened Skin',
    b'Reht': 'Upgrade Hippogryph Taming',
    b'Reib': 'Upgrade Improved Bows',
    b'Rema': 'Upgrade Moon Armor',
    b'Remg': 'Upgrade Moon Glaive',
    b'Remk': 'Upgrade Marksmanship',
    b'Renb': 'Upgrade Nature\'s Blessing',
    b'Repd': 'Upgrade Vorpal Blades',
    b'Rerh': 'Upgrade Reinforced Hides',
    b'Rers': 'Upgrade Resistant Skin',
    b'Resc': 'Upgrade Sentinel',
    b'Resi': 'Upgrade Abolish Magic',
    b'Resm': 'Upgrade Strength of the Moon',
    b'Resw': 'Upgrade Strength of the Wild',
    b'Reuv': 'Upgrade Ultravision',
    b'Rews': 'Upgrade Well Sprint',
    b'Rhaa': 'Upgrade ARTILLERY',
    b'Rhac': 'Upgrade Masonry',
    b'Rhan': 'Upgrade Animal War Training',
    b'Rhar': 'Upgrade Plating',
    b'Rhcd': 'Upgrade Cloud',
    b'Rhde': 'Upgrade Defend',
    b'Rhfc': 'Upgrade Flak Cannons',
    b'Rhfs': 'Upgrade Fragmentation Shards',
    b'Rhgb': 'Upgrade Flying Machine Bombs',
    b'Rhhb': 'Upgrade Storm Hammers',
    b'Rhla': 'Upgrade Leather Armor',
    b'Rhlh': 'Upgrade Lumber Harvesting',
    b'Rhme': 'Upgrade Melee Weapons',
    b'Rhmi': 'Upgrade GOLD',
    b'Rhpt': 'Upgrade Priest Training',
    b'Rhra': 'Upgrade Ranged Weapons',
    b'Rhri': 'Upgrade Long Rifles',
    b'Rhrt': 'Upgrade Barrage',
    b'Rhse': 'Upgrade Magic Sentry',
    b'Rhsr': 'Upgrade Flare',
    b'Rhss': 'Upgrade Control Magic',
    b'Rhst': 'Upgrade Sorceress Training',
    b'Rnam': 'Upgrade Naga Armor',
    b'Rnat': 'Upgrade Naga Attack',
    b'Rnen': 'Upgrade Naga Ensnare',
    b'Rnsi': 'Upgrade Naga Abolish Magic',
    b'Rnsw': 'Upgrade Siren',
    b'Roaa': 'Upgrade Orc Artillery',
    b'Roar': 'Upgrade Unit Armor',
    b'Robf': 'Upgrade Burning Oil',
    b'Robk': 'Upgrade Berserker Upgrade',
    b'Robs': 'Upgrade Berserker Strength',
    b'Roch': 'Upgrade Chaos',
    b'Roen': 'Upgrade Ensnare',
    b'Rolf': 'Upgrade Liquid Fire',
    b'Rome': 'Upgrade Melee Weapons',
    b'Ropg': 'Upgrade Pillage',
    b'Rora': 'Upgrade Ranged Weapons',
    b'Rorb': 'Upgrade Reinforced Defenses',
    b'Rosp': 'Upgrade Spiked Barricades',
    b'Rost': 'Upgrade Shaman Training',
    b'Rotr': 'Upgrade Troll Regeneration',
    b'Rovs': 'Upgrade Envenomed Spears',
    b'Rowd': 'Upgrade Witch Doctor Training',
    b'Rows': 'Upgrade Pulverize',
    b'Rowt': 'Upgrade Spirit Walker Training',
    b'Ruab': 'Upgrade ABOM',
    b'Ruac': 'Upgrade Cannibalize',
    b'Ruar': 'Upgrade Unholy Armor',
    b'Ruax': 'Upgrade ABOM_EXPL',
    b'Ruba': 'Upgrade Banshee Training',
    b'Rubu': 'Upgrade Burrow',
    b'Rucr': 'Upgrade Creature Carapace',
    b'Ruex': 'Upgrade Exhume Corpses',
    b'Rufb': 'Upgrade Freezing Breath',
    b'Rugf': 'Upgrade Ghoul Frenzy',
    b'Rume': 'Upgrade Unholy Strength',
    b'Rump': 'Upgrade MEAT_WAGON',
    b'Rune': 'Upgrade Necromancer Training',
    b'Rupc': 'Upgrade Disease Cloud',
    b'Rura': 'Upgrade Creature Attack',
    b'Rurs': 'Upgrade SACRIFICE',
    b'Rusf': 'Upgrade Stone Form',
    b'Rusl': 'Upgrade Skeletal Longevity',
    b'Rusm': 'Upgrade Skeletal Mastery',
    b'Rusp': 'Upgrade Destroyer Form',
    b'Ruwb': 'Upgrade Web',
    b'Rwdm': 'Upgrade War Drums Damage Increase',
    b'uabo': 'Abomination',
    b'uaco': 'Acolyte',
    b'uaod': 'Altar of Darkness',
    b'uarb': 'Undead Barge',
    b'uban': 'Banshee',
    b'ubon': 'Boneyard',
    b'ubsp': 'Destroyer',
    b'Ucrl': 'Crypt Lord',
    b'ucry': 'Pit Fiend',
    b'Udea': 'Death Knight',
    b'Udre': 'Dread Lord',
    b'Udth': 'Detheroc',
    b'ufro': 'Frost Wyrm',
    b'ugar': 'Gargoyle',
    b'ugho': 'Ghoul',
    b'ugol': 'Haunted Gold Mine',
    b'ugrm': 'Gargoyle (Stone)',
    b'ugrv': 'Graveyard',
    b'ugsp': 'Gargoyle Spire',
    b'Ulic': 'Lich',
    b'Umal': 'Malganis',
    b'umtw': 'Meat Wagon',
    b'unec': 'Necromancer',
    b'unp1': 'Halls of the Dead',
    b'unp2': 'Black Citadel',
    b'unpl': 'Necropolis',
    b'uobs': 'Obsidian Statue',
    b'usap': 'Sacrificial Pit',
    b'usep': 'Crypt',
    b'ushd': 'Shade',
    b'uske': 'Skeleton Warrior',
    b'uslh': 'Slaughterhouse',
    b'Utic': 'Tichondrius',
    b'utod': 'Temple of the Damned',
    b'utom': 'Tomb of Relics',
    b'uzg1': 'Spirit Tower',
    b'uzg2': 'Nerubian Tower',
    b'uzig': 'Ziggurat',
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

class Event(object):
    """An event base class."""

    def __init__(self, f):
        self.f = f
        self.time = f._clock

    def strtime(self):
        secs = self.time / 1000.0
        s = secs % 60
        m = int(secs / 60) % 60
        h = int(secs / 3600)
        rtn = []
        if h > 0: 
            rtn.append("{0:02}".format(h))
        if m > 0: 
            rtn.append("{0:02}".format(m))
        rtn.append("{0:06.3f}".format(s))
        return ":".join(rtn)

class Chat(Event):

    def __init__(self, f, player_id, mode, msg):
        super(Chat, self).__init__(f)
        self.player_id = player_id
        self.mode = mode
        self.msg = msg

    def __str__(self):
        t = self.strtime()
        p = self.f.player_name(self.player_id)
        m = self.strmode()
        return "[{t}] <{m}> {p}: {msg}".format(t=t, p=p, m=m, msg=self.msg)

    def strmode(self):
        mode = self.mode
        if not mode.startswith('player'):
            return mode
        pid = int(mode[6:])
        return self.f.player_name(pid)

class LeftGame(Event):

    remote_results = {
        0x01: 'left',
        0x07: 'left',
        0x08: 'lost',
        0x09: 'won',
        0x0A: 'draw',
        0x0B: 'left',
        }

    local_not_last_results = {
        0x01: 'disconnected',
        0x07: 'lost',
        0x08: 'lost',
        0x09: 'won',
        0x0A: 'draw',
        0x0B: 'lost',
        }

    local_last_results = {
        0x01: 'disconnected',
        0x08: 'lost',
        0x09: 'won',
        }

    def __init__(self, f, player_id, closedby, resultflag, inc, unknownflag):
        super(LeftGame, self).__init__(f)
        self.player_id = player_id
        self.closedby = closedby
        self.resultflag = resultflag
        self.inc = inc
        self.unknownflag = unknownflag
        self.next = None

    def __str__(self):
        t = self.strtime()
        p = self.f.player_name(self.player_id)
        r = self.result()
        rtn = "[{t}] <{cb}> {p} left game, {r}"
        return rtn.format(t=t, p=p, cb=self.closedby, r=r)

    def result(self):
        cb = self.closedby
        res = self.resultflag
        if cb == 'remote':
            r = self.remote_results[res]
        elif cb == 'local':
            if self.next is None:
                if res == 0x07 or res == 0x0B:
                    r = 'won' if self.inc else 'lost'
                else:
                    r = self.local_last_results[res]
            else:
                r = self.local_not_last_results[res]
        else:
            r = 'left'
        return r

class Countdown(Event):

    def __init__(self, f, mode, secs):
        super(Countdown, self).__init__(f)
        self.mode = mode
        self.secs = secs

    def __str__(self):
        t = self.strtime()
        rtn = "[{t}] Game countdown {mode}, {m:02}:{s:02} left"
        return rtn.format(t=t, mode=self.mode, m=int(self.secs/60), s=self.secs%60)

class Action(Event):

    id = -1
    size = 1

    def __init__(self, f, player_id, action_block):
        super(Action, self).__init__(f)
        self.player_id = player_id

    def __str__(self):
        t = self.strtime()
        p = self.f.player_name(self.player_id)
        rtn = "[{t}] <{c}> {p}"
        return rtn.format(t=t, c=self.__class__.__name__, p=p)

class Pause(Action):

    id = 0x01

    def __init__(self, f, player_id, action_block):
        super(Pause, self).__init__(f, player_id, action_block)

class Resume(Action):

    id = 0x02

    def __init__(self, f, player_id, action_block):
        super(Resume, self).__init__(f, player_id, action_block)

class SetGameSpeed(Action):

    id = 0x03
    size = 2

    def __init__(self, f, player_id, action_block):
        super(SetGameSpeed, self).__init__(f, player_id, action_block)
        self.speed = b2i(action_block[1])

    def __str__(self):
        s = super(SetGameSpeed, self).__str__()
        return '{0} - {1}'.format(s, SPEEDS[self.speed])

class IncreaseGameSpeed(Action):

    id = 0x04

    def __init__(self, f, player_id, action_block):
        super(IncreaseGameSpeed, self).__init__(f, player_id, action_block)

class DecreaseGameSpeed(Action):

    id = 0x05

    def __init__(self, f, player_id, action_block):
        super(DecreaseGameSpeed, self).__init__(f, player_id, action_block)

class SaveGame(Action):

    id = 0x06
    size = None

    def __init__(self, f, player_id, action_block):
        super(SaveGame, self).__init__(f, player_id, action_block)
        self.name, n = nulltermstr(action_block[1:])
        self.size = 1 + n + 1

    def __str__(self):
        s = super(SaveGame, self).__str__()
        return '{0} - {1}'.format(s, self.name)

class SaveGameFinished(Action):

    id = 0x07
    size = 5

    def __init__(self, f, player_id, action_block):
        super(SaveGameFinished, self).__init__(f, player_id, action_block)

class Ability(Action):

    id = 0x10

    def __init__(self, f, player_id, action_block):
        super(Ability, self).__init__(f, player_id, action_block)
        offset = 1
        o = 1 if f.build_num < BUILD_1_13 else WORD
        self.flags = b2i(action_block[offset:offset+o])
        offset += o
        self.item = item = action_block[offset:offset+DWORD]
        if item[-2:] != NUMERIC_ITEM:
            self.item = item[::-1]
        offset += DWORD
        offset += 2 * DWORD if f.build_num >= BUILD_1_07 else 0
        self.size = self.offset = offset

    def __str__(self):
        s = super(Ability, self).__str__()
        return '{0} - {1}'.format(s, ITEMS.get(self.item, self.item))

class AbilityPositionObject(Action):

    id = 0x12
    size = 30

    def __init__(self, f, player_id, action_block):
        super(AbilityPositionObject, self).__init__(f, player_id, action_block)

# has to come after the action classes 
ACTIONS = {a.id: a for a in locals().values() if hasattr(a, 'id') and \
                                    isinstance(a.id, int) and a.id > 0}

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
        data = b''
        for n in range(self.nblocks):
            block_size = b2i(f.read(WORD))
            block_size_decomp = b2i(f.read(WORD))
            self.loc += DWORD
            raw = f.read(block_size)
            dat = zlib.decompress(raw)
            if len(dat) != block_size_decomp:
                raise zlib.error("Decompressed data size does not match expected size.")
            data += dat
        self._parse_blocks(data)

    def _parse_blocks(self, data):
        self.events = []
        self._clock = 0
        self._lastleft = None
        _parsers = {
            0x17: self._parse_leave_game,
            0x1A: lambda data: 5,
            0x1B: lambda data: 5,
            0x1C: lambda data: 5,
            0x1E: self._parse_time_slot,  # old blockid
            0x1F: self._parse_time_slot,  # new blockid
            0x20: self._parse_chat,
            0x22: lambda data: 6,
            0x23: lambda data: 11,
            0x2F: self._parse_countdown,
            }
        offset = self._parse_startup(data)
        data = data[offset:]
        blockid = b2i(data[0])
        while blockid != 0:
            offset = _parsers[blockid](data)
            data = data[offset:]
            blockid = b2i(data[0])

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
        self.game_speed = SPEEDS[bitfield(settings[0], slice(2))]
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
        self.random_seed = data[offset:offset+DWORD]
        offset += DWORD
        self.select_mode = SELECT_MODES[b2i(data[offset])]
        offset += 1
        self.num_start_positions = b2i(data[offset])
        offset += 1
        return offset

    def _parse_leave_game(self, data):
        offset = 1
        reason = b2i(data[offset:offset+DWORD])
        offset += DWORD
        player_id = b2i(data[offset])
        offset += 1
        res = b2i(data[offset:offset+DWORD])
        offset += DWORD
        unknownflag = b2i(data[offset:offset+DWORD])
        offset += DWORD
        # compute inc
        if self._lastleft is None:
            inc = False
        else:
            inc = (unknownflag == (self._lastleft.unknownflag + 1))
        # compute closedby and reult
        if reason == 0x01:
            closedby = 'remote'
        elif reason == 0x0C:
            closedby = 'local'
        else: 
            closedby = 'unknown'
        e = LeftGame(self, player_id, closedby, res, inc, unknownflag)
        self.events.append(e)
        if self._lastleft is not None:
            self._lastleft.next = e
        self._lastleft = e
        return 14

    def _parse_time_slot(self, data):
        n = b2i(data[1:1+WORD])
        offset = 1 + WORD
        dt = b2i(data[offset:offset+WORD])
        offset += WORD
        cmddata = data[offset:n+3]
        while len(cmddata) > 0:
            player_id = b2i(cmddata[0])
            i = b2i(cmddata[1:1+WORD])
            action_block = cmddata[1+WORD:i+1+WORD]
            self._parse_actions(player_id, action_block)
            cmddata = cmddata[i+1+WORD:]
        self._clock += dt
        return n + 3

    def _parse_chat(self, data):
        player_id = b2i(data[1])
        n = b2i(data[2:2+WORD])
        offset = 2 + WORD
        flags = b2i(data[offset])
        offset += 1
        if flags == 0x10:
            mode = 'startup'
        else:
            m = b2i(data[offset:offset+DWORD])
            offset += DWORD
            mode = CHAT_MODES.get(m, None)
            if mode is None:
                mode = 'player{0}'.format(m - 0x3)
        msg, _ = nulltermstr(data[offset:])
        self.events.append(Chat(self, player_id, mode, msg))
        return n + 4

    def _parse_countdown(self, data):
        offset = 1
        m = b2i(data[offset:offset+DWORD])
        offset += DWORD
        mode = 'running' if m == 0x00 else 'over'
        secs = b2i(data[offset:offset+DWORD])
        offset += DWORD
        e = Countdown(self, mode, secs)
        self.events.append(e)
        return 9

    def _parse_actions(self, player_id, action_block):
        while len(action_block) > 0:
            aid = b2i(action_block[0])
            action = ACTIONS.get(aid, None)
            if action is None:
                return 
            e = action(self, player_id, action_block)
            self.events.append(e)
            action_block = action_block[e.size:]

    @lru_cache(13)
    def player(self, pid):
        players = self.players
        if pid < len(players):
            p = players[pid]
            if p.id == pid:
                return p
        for p in players:
            if p.id == pid:
                break
        else:
            p = self.slot_records[pid]
        return p

    @lru_cache(13)
    def player_name(self, pid):
        p = self.player(pid)
        if isinstance(p, SlotRecord):
            return 'observer'
        return p.name

if __name__ == '__main__':
    f = File(sys.argv[1])
    for event in f.events:
        print(event)
    print(f.version_num)
    print(f.build_num)
