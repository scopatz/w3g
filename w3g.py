"""Implements the basic w3g file class. Based on information available at

* http://w3g.deepnode.de/files/w3g_format.txt

:author: scopz <scopatz@gmail.com>
"""
from __future__ import unicode_literals, print_function
import io
import sys
import base64
import zlib
import struct
import binascii
from collections import namedtuple

__version__ = '1.0.5'

WORD = 2   # bytes
DWORD = 4  # bytes, double word
NULLSTR = b'\0'
MAXPOS = 16384.0  # maps may range from -MAXPOS to MAXPOS with (0, 0) at the center

# build number associated with v1.07 of the game
BUILD_1_06 = 4656

# build number associated with v1.07 of the game
BUILD_1_07 = 6031

# build number associated with v1.13 of the game
BUILD_1_13 = 6037

# build number associated with v1.14b of the game
BUILD_1_14B = 6040

if sys.version_info[0] < 3:
    BLENFLAG = {1: 'B', WORD: 'H', DWORD: 'L', 8: 'Q'}
    b2i = lambda b: struct.unpack('<' + BLENFLAG[len(b)], b)[0]

    # to print unicode
    import codecs
    UTF8Writer = codecs.getwriter('utf8')
    utf8writer = UTF8Writer(sys.stdout)
    def umake(f):
        def uprint(*objects, **kw):
            uo = map(unicode, objects)
            if 'file' not in kw:
                kw['file'] = utf8writer
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
    i = b.find(NULLSTR)
    try:
        s = b[:i].decode('utf-8')
    except:
        s = b[:i].decode('latin-1')
    return s, i

def fixedlengthstr(b, i):
    """Returns a string of length i from bytes"""
    s = b[:i].decode('utf-8')
    return s

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

def b2f(b):
    return struct.unpack('<f', b)[0]

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
# Use RGB hex values for new colors because they are strange
COLORS = ('red', 'blue', 'cyan', 'purple',
          'yellow', 'orange', 'green', 'pink',
          'gray', 'light blue', 'dark green', 'brown',
          '9B0000', '0000C3', '00EAFF', 'BE00FE',
          'EBCD87', 'F8A48B', 'BFFF80', 'DCB9EB',
          '282828', 'EBF0FF', '00781E', 'A46F33',
          'observer')
AI_STRENGTH = {0x00: 'easy', 0x01: 'normal', 0x02: 'insane'}
SELECT_MODES = {
    0x00: 'team & race selectable',
    0x01: 'team not selectable',
    0x03: 'team & race not selectable',
    0x04: 'race fixed to random',
    0xcc: 'automated match making',
    0xac: 'automated match making',
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
    b'nsfp': 'Forest Troll Shadow Priest',
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
    # Others
    b'nskf': 'Burning Archer',
    b'nws1': 'Dragon Hawk',
    b'nban': 'Bandit',
    b'nrog': 'Rogue',
    b'nenf': 'Enforcer',
    b'nass': 'Assassin',
    b'nbdk': 'Black Drake',
    b'nrdk': 'Red Dragon Whelp',
    b'nbdr': 'Black Dragon Whelp',
    b'nrdr': 'Red Drake',
    b'nbwm': 'Black Dragon',
    b'nrwm': 'Red Dragon',
    b'nadr': 'Blue Dragon',
    b'nadw': 'Blue Dragon Whelp',
    b'nadk': 'Blue Drake',
    b'nbzd': 'Bronze Dragon',
    b'nbzk': 'Bronze Drake',
    b'nbzw': 'Bronze Dragon Whelp',
    b'ngrd': 'Green Dragon',
    b'ngdk': 'Green Drake',
    b'ngrw': 'Green Dragon Whelp',
    b'ncea': 'Centaur Archer',
    b'ncen': 'Centaur Outrunner',
    b'ncer': 'Centaur Drudge',
    b'ndth': 'Dark Troll High Priest',
    b'ndtp': 'Dark Troll Shadow Priest',
    b'ndtb': 'Dark Troll Berserker',
    b'ndtw': 'Dark Troll WarLord',
    b'ndtr': 'Dark Troll',
    b'ndtt': 'Dark Troll Trapper',
    b'nfsh': 'Forest Troll High Priest',
    b'nfsp': 'Forest Troll Shadow Priest',
    b'nftr': 'Forest Troll',
    b'nftb': 'Forest Troll Berserker',
    b'nftt': 'Forest Troll Trapper',
    b'nftk': 'Forest Troll WarLord',
    b'ngrk': 'Mud Golem',
    b'ngir': 'Goblin Shredder',
    b'nfrs': 'Furbolg Shaman',
    b'ngna': 'Gnoll Poacher',
    b'ngns': 'Gnoll Assassin',
    b'ngno': 'Gnoll',
    b'ngnb': 'Gnoll Brute',
    b'ngnw': 'Gnoll Warden',
    b'ngnv': 'Gnoll Overseer',
    b'ngsp': 'Goblin Sapper',
    b'nhrr': 'Harpy Rogue',
    b'nhrw': 'Harpy Windwitch',
    b'nits': 'Ice Troll Berserker',
    b'nitt': 'Ice Troll Trapper',
    b'nkob': 'Kobold',
    b'nkog': 'Kobold Geomancer',
    b'nthl': 'Thunder Lizard',
    b'nmfs': 'Murloc Flesheater',
    b'nmrr': 'Murloc Huntsman',
    b'nowb': 'Wildkin',
    b'nrzm': 'Razormane Medicine Man',
    b'nnwa': 'Nerubian Warrior',
    b'nnwl': 'Nerubian Webspinner',
    b'nogr': 'Ogre Warrior',
    b'nogm': 'Ogre Mauler',
    b'nogl': 'Ogre Lord',
    b'nomg': 'Ogre Magi',
    b'nrvs': 'Frost Revenant',
    b'nslf': 'Sludge Flinger',
    b'nsts': 'Satyr Shadowdancer',
    b'nstl': 'Satyr Soulstealer',
    b'nzep': 'Goblin Zeppelin',
    b'ntrt': 'Giant Sea Turtle',
    b'nlds': 'Makrura Deepseer',
    b'nlsn': 'Makrura Snapper',
    b'nmsn': 'Mur\'gul Snarecaster',
    b'nscb': 'Spider Crab Shorecrawler',
    b'nbot': 'Transport Ship',
    b'nsc2': 'Spider Crab Limbripper',
    b'nsc3': 'Spider Crab Behemoth',
    b'nbdm': 'Blue Dragonspawn Meddler',
    b'nmgw': 'Magnataur Warrior',
    b'nanb': 'Barbed Arachnathid',
    b'nanm': 'Barbed Arachnathid',
    b'nfps': 'Polar Furbolg Shaman',
    b'nmgv': 'Magic Vault',
    b'nitb': 'Icy Treasure Box',
    b'npfl': 'Fel Beast',
    b'ndrd': 'Draenei Darkslayer',
    b'ndrm': 'Draenei Disciple',
    b'nvdw': 'Voidwalker',
    b'nvdg': 'Greater Voidwalker',
    b'nnht': 'Nether Dragon Hatchling',
    b'nndk': 'Nether Drake',
    b'nndr': 'Nether Dragon',
    # real items
    b'LTlt': 'Tree',
    b'nmer': 'Merchant',
    b'ntav': 'Tavern',
    b'ngol': 'Goldmine',
    b'amrc': 'Amulet of Recall',
    b'ankh': 'Ankh of Reincarnation',
    b'belv': 'Boots of Quel\'Thalas +6',
    b'bgst': 'Belt of Giant Strength +6',
    b'bspd': 'Boots of Speed',
    b'ccmd': 'Scepter of Mastery',
    b'ciri': 'Robe of the Magi +6',
    b'ckng': 'Crown of Kings +5',
    b'clsd': 'Cloak of Shadows',
    b'crys': 'Crystal Ball',
    b'desc': 'Kelen\'s Dagger of Escape',
    b'gemt': 'Gem of True Seeing',
    b'gobm': 'Goblin Land Mines',
    b'gsou': 'Soul Gem',
    b'guvi': 'Glyph of Ultravision',
    b'gfor': 'Glyph of Fortification',
    b'soul': 'Soul',
    b'mdpb': 'Medusa Pebble',
    b'rag1': 'Slippers of Agility +3',
    b'rat3': 'Claws of Attack +3',
    b'rin1': 'Mantle of Intelligence +3',
    b'rde1': 'Ring of Protection +2',
    b'rde2': 'Ring of Protection +3',
    b'rde3': 'Ring of Protection +4',
    b'rhth': 'Khadgar\'s Gem of Health',
    b'rst1': 'Gauntlets of Ogre Strength +3',
    b'ofir': 'Orb of Fire',
    b'ofro': 'Orb of Frost',
    b'olig': 'Orb of Lightning',
    b'oli2': 'Orb of Lightning',
    b'oven': 'Orb of Venom',
    b'odef': 'Orb of Darkness',
    b'ocor': 'Orb of Corruption',
    b'pdiv': 'Potion of Divinity',
    b'phea': 'Potion of Healing',
    b'pghe': 'Potion of Greater Healing',
    b'pinv': 'Potion of Invisibility',
    b'pgin': 'Potion of Greater Invisibility',
    b'pman': 'Potion of Mana',
    b'pgma': 'Potion of Greater Mana',
    b'pnvu': 'Potion of Invulnerability',
    b'pnvl': 'Potion of Lesser Invulnerability',
    b'pres': 'Potion of Restoration',
    b'pspd': 'Potion of Speed',
    b'rlif': 'Ring of Regeneration',
    b'rwiz': 'Sobi Mask',
    b'sfog': 'Horn of the Clouds',
    b'shea': 'Scroll of Healing',
    b'sman': 'Scroll of Mana',
    b'spro': 'Scroll of Protection',
    b'sres': 'Scroll of Restoration',
    b'ssil': 'Staff of Silence',
    b'stwp': 'Scroll of Town Portal',
    b'tels': 'Goblin Night Scope',
    b'tdex': 'Tome of Agility',
    b'texp': 'Tome of Experience',
    b'tint': 'Tome of Intelligence',
    b'tkno': 'Tome of Power',
    b'tstr': 'Tome of Strength',
    b'ward': 'Warsong Battle Drums',
    b'will': 'Wand of Illusion',
    b'wneg': 'Wand of Negation',
    b'rdis': 'Rune of Dispel Magic',
    b'rwat': 'Rune of the Watcher',
    b'fgrd': 'Red Drake Egg',
    b'fgrg': 'Stone Token',
    b'fgdg': 'Demonic Figurine',
    b'fgfh': 'Spiked Collar',
    b'fgsk': 'Book of the Dead',
    b'engs': 'Enchanted Gemstone',
    b'k3m1': 'Mooncrystal',
    b'modt': 'Mask of Death',
    b'sand': 'Scroll of Animate Dead',
    b'srrc': 'Scroll of Resurrection',
    b'sror': 'Scroll of the Beast',
    b'infs': 'Inferno Stone',
    b'shar': 'Ice Shard',
    b'wild': 'Amulet of the Wild',
    b'wswd': 'Sentry Wards',
    b'whwd': 'Healing Wards',
    b'wlsd': 'Wand of Lightning Shield',
    b'wcyc': 'Wand of the Wind',
    b'rnec': 'Rod of Necromancy',
    b'pams': 'Anti-magic Potion',
    b'clfm': 'Cloak of Flames',
    b'evtl': 'Talisman of Evasion',
    b'nspi': 'Necklace of Spell Immunity',
    b'lhst': 'The Lion Horn of Stormwind',
    b'kpin': 'Khadgar\'s Pipe of Insight',
    b'sbch': 'Scourge Bone Chimes',
    b'afac': 'Alleria\'s Flute of Accuracy',
    b'ajen': 'Ancient Janggo of Endurance',
    b'lgdh': 'Legion Doom-Horn',
    b'hcun': 'Hood of Cunning',
    b'mcou': 'Medallion of Courage',
    b'hval': 'Helm of Valor',
    b'cnob': 'Circlet of Nobility',
    b'prvt': 'Periapt of Vitality',
    b'tgxp': 'Tome of Greater Experience',
    b'mnst': 'Mana Stone',
    b'hlst': 'Health Stone',
    b'tpow': 'Tome of Knowledge',
    b'tst2': 'Tome of Strength +2',
    b'tin2': 'Tome of Intelligence +2',
    b'tdx2': 'Tome of Agility +2',
    b'rde0': 'Ring of Protection +1',
    b'rde4': 'Ring of Protection +5',
    b'rat6': 'Claws of Attack +6',
    b'rat9': 'Claws of Attack +9',
    b'ratc': 'Claws of Attack +12',
    b'ratf': 'Claws of Attack +15',
    b'manh': 'Manual of Health',
    b'pmna': 'Pendant of Mana',
    b'penr': 'Pendant of Energy',
    b'gcel': 'Gloves of Haste',
    b'totw': 'Talisman of the Wild',
    b'phlt': 'Phat Lewt',
    b'gopr': 'Glyph of Purification',
    b'ches': 'Cheese',
    b'mlst': 'Maul of Strength',
    b'rnsp': 'Ring of Superiority',
    b'brag': 'Bracer of Agility',
    b'sksh': 'Skull Shield',
    b'vddl': 'Voodoo Doll',
    b'sprn': 'Spider Ring',
    b'tmmt': 'Totem of Might',
    b'anfg': 'Ancient Figurine',
    b'lnrn': 'Lion\'s Ring',
    b'iwbr': 'Ironwood Branch',
    b'jdrn': 'Jade Ring',
    b'drph': 'Druid Pouch',
    b'hslv': 'Healing Salve',
    b'pclr': 'Clarity Potion',
    b'plcl': 'Lesser Clarity Potion',
    b'rej1': 'Minor Replenishment Potion',
    b'rej2': 'Lesser Replenishment Potion',
    b'rej3': 'Replenishment Potion',
    b'rej4': 'Greater Replenishment Potion',
    b'rej5': 'Lesser Scroll of Replenishment',
    b'rej6': 'Greater Scroll of Replenishment',
    b'sreg': 'Scroll of Regeneration',
    b'gold': 'Gold Coins',
    b'lmbr': 'Bundle of Lumber',
    b'fgun': 'Flare Gun',
    b'pomn': 'Potion of Omniscience',
    b'gomn': 'Glyph of Omniscience',
    b'wneu': 'Wand of Neutralization',
    b'silk': 'Spider Silk Broach',
    b'lure': 'Monster Lure',
    b'skul': 'Sacrificial Skull',
    b'moon': 'Moonstone',
    b'brac': 'Runed Bracers',
    b'vamp': 'Vampiric Potion',
    b'woms': 'Wand of Mana Stealing',
    b'tcas': 'Tiny Castle',
    b'tgrh': 'Tiny Great Hall',
    b'tsct': 'Ivory Tower',
    b'wshs': 'Wand of Shadowsight',
    b'tret': 'Tome of Retraining',
    b'sneg': 'Staff of Negation',
    b'stel': 'Staff of Teleportation',
    b'spre': 'Staff of Preservation',
    b'mcri': 'Mechanical Critter',
    b'spsh': 'Amulet of Spell Shield',
    b'sbok': 'Spell Book',
    b'ssan': 'Staff of Sanctuary',
    b'shas': 'Scroll of Speed',
    b'dust': 'Dust of Appearance',
    b'oslo': 'Orb of Slow',
    b'dsum': 'Diamond of Summoning',
    b'sor1': 'Shadow Orb +1',
    b'sor2': 'Shadow Orb +2',
    b'sor3': 'Shadow Orb +3',
    b'sor4': 'Shadow Orb +4',
    b'sor5': 'Shadow Orb +5',
    b'sor6': 'Shadow Orb +6',
    b'sor7': 'Shadow Orb +7',
    b'sor8': 'Shadow Orb +8',
    b'sor9': 'Shadow Orb +9',
    b'sora': 'Shadow Orb +10',
    b'sorf': 'Shadow Orb Fragment',
    b'fwss': 'Frost Wyrm Skull Shield',
    b'ram1': 'Ring of the Archmagi',
    b'ram2': 'Ring of the Archmagi',
    b'ram3': 'Ring of the Archmagi',
    b'ram4': 'Ring of the Archmagi',
    b'shtm': 'Shamanic Totem',
    b'shwd': 'Shimmerweed',
    b'btst': 'Battle Standard',
    b'skrt': 'Skeletal Artifact',
    b'thle': 'Thunder Lizard Egg',
    b'sclp': 'Secret Level Powerup',
    b'gldo': 'Orb of Kil\'jaeden',
    b'tbsm': 'Tiny Blacksmith',
    b'tfar': 'Tiny Farm',
    b'tlum': 'Tiny Lumber Mill',
    b'tbar': 'Tiny Barracks',
    b'tbak': 'Tiny Altar of Kings',
    b'mgtk': 'Magic Key Chain',
    b'stre': 'Staff of Reanimation',
    b'horl': 'Sacred Relic',
    b'hbth': 'Helm of Battlethirst',
    b'blba': 'Bladebane Armor',
    b'rugt': 'Runed Gauntlets',
    b'frhg': 'Firehand Gauntlets',
    b'gvsm': 'Gloves of Spell Mastery',
    b'crdt': 'Crown of the DeathLord',
    b'arsc': 'Arcane Scroll',
    b'scul': 'Scroll of the Unholy Legion',
    b'tmsc': 'Tome of Sacrifices',
    b'dtsb': 'Drek\'thar\'s Spellbook',
    b'grsl': 'Grimoire of Souls',
    b'arsh': 'Arcanite Shield',
    b'shdt': 'Shield of the DeathLord',
    b'shhn': 'Shield of Honor',
    b'shen': 'Enchanted Shield',
    b'thdm': 'Thunderlizard Diamond',
    b'stpg': 'Clockwork Penguin',
    b'shrs': 'Shimmerglaze Roast',
    b'bfhr': 'Bloodfeather\'s Heart',
    b'cosl': 'Celestial Orb of Souls',
    b'shcw': 'Shaman Claws',
    b'srbd': 'Searing Blade',
    b'frgd': 'Frostguard',
    b'envl': 'Enchanted Vial',
    b'rump': 'Rusty Mining Pick',
    b'mort': 'Mogrin\'s Report',
    b'srtl': 'Serathil',
    b'stwa': 'Sturdy War Axe',
    b'klmm': 'Killmaim',
    b'rots': 'Scepter of the Sea',
    b'axas': 'Ancestral Staff',
    b'mnsf': 'Mindstaff',
    b'schl': 'Scepter of Healing',
    b'asbl': 'Assassin\'s Blade',
    b'kgal': 'Keg of Ale',
    b'dphe': 'Thunder Phoenix Egg',
    b'dkfw': 'Keg of Thunderwater',
    b'dthb': 'Thunderbloom Bulb',
    # extra heros
    b'Npbm': 'Pandaren Brewmaster',
    b'Nbrn': 'Dark Ranger',
    b'Nngs': 'Naga Sea Witch',
    b'Nplh': 'Pit Lord',
    b'Nbst': 'Beastmaster',
    b'Ntin': 'Goblin Tinker',
    b'Nfir': 'FireLord',
    b'Nalc': 'Goblin Alchemist',
    # extra hero abilities
    b'AHbz': 'Archmage:Blizzard',
    b'AHwe': 'Archmage:Summon Water Elemental',
    b'AHab': 'Archmage:Brilliance Aura',
    b'AHmt': 'Archmage:Mass Teleport',
    b'AHtb': 'Mountain King:Storm Bolt',
    b'AHtc': 'Mountain King:Thunder Clap',
    b'AHbh': 'Mountain King:Bash',
    b'AHav': 'Mountain King:Avatar',
    b'AHhb': 'Paladin:Holy Light',
    b'AHds': 'Paladin:Divine Shield',
    b'AHad': 'Paladin:Devotion Aura',
    b'AHre': 'Paladin:Resurrection',
    b'AHdr': 'Blood Mage:Siphon Mana',
    b'AHfs': 'Blood Mage:Flame Strike',
    b'AHbn': 'Blood Mage:Banish',
    b'AHpx': 'Blood Mage:Summon Phoenix',
    b'AEmb': 'Demon Hunter:Mana Burn',
    b'AEim': 'Demon Hunter:Immolation',
    b'AEev': 'Demon Hunter:Evasion',
    b'AEme': 'Demon Hunter:Metamorphosis',
    b'AEer': 'Keeper of the Grove:Entangling Roots',
    b'AEfn': 'Keeper of the Grove:Force of Nature',
    b'AEah': 'Keeper of the Grove:Thorns Aura',
    b'AEtq': 'Keeper of the Grove:Tranquility',
    b'AEst': 'Priestess of the Moon:Scout',
    b'AHfa': 'Priestess of the Moon:Searing Arrows',
    b'AEar': 'Priestess of the Moon:Trueshot Aura',
    b'AEsf': 'Priestess of the Moon:Starfall',
    b'AEbl': 'Warden:Blink',
    b'AEfk': 'Warden:Fan of Knives',
    b'AEsh': 'Warden:Shadow Strike',
    b'AEsv': 'Warden:Spirit of Vengeance',
    b'AOwk': 'Blademaster:Wind Walk',
    b'AOmi': 'Blademaster:Mirror Image',
    b'AOcr': 'Blademaster:Critical Strike',
    b'AOww': 'Blademaster:Bladestorm',
    b'AOcl': 'Far Seer:Chain Lighting',
    b'AOfs': 'Far Seer:Far Sight',
    b'AOsf': 'Far Seer:Feral Spirit',
    b'AOeq': 'Far Seer:Earth Quake',
    b'AOsh': 'Tauren Chieftain:Shockwave',
    b'AOae': 'Tauren Chieftain:Endurance Aura',
    b'AOws': 'Tauren Chieftain:War Stomp',
    b'AOre': 'Tauren Chieftain:Reincarnation',
    b'AOhw': 'Shadow Hunter:Healing Wave',
    b'AOhx': 'Shadow Hunter:Hex',
    b'AOsw': 'Shadow Hunter:Serpent Ward',
    b'AOvd': 'Shadow Hunter:Big Bad Voodoo',
    b'AUdc': 'Death Knight:Death Coil',
    b'AUdp': 'Death Knight:Death Pact',
    b'AUau': 'Death Knight:Unholy Aura',
    b'AUan': 'Death Knight:Animate Dead',
    b'AUcs': 'Dreadlord:Carrion Swarm',
    b'AUsl': 'Dreadlord:Sleep',
    b'AUav': 'Dreadlord:Vampiric Aura',
    b'AUin': 'Dreadlord:Inferno',
    b'AUfn': 'Lich:Frost Nova',
    b'AUfa': 'Lich:Frost Armor',
    b'AUfu': 'Lich:Frost Armor',
    b'AUdr': 'Lich:Dark Ritual',
    b'AUdd': 'Lich:Death and Decay',
    b'AUim': 'Crypt Lord:Impale',
    b'AUts': 'Crypt Lord:Spiked Carapace',
    b'AUcb': 'Crypt Lord:Carrion Beetles',
    b'AUls': 'Crypt Lord:Locust Swarm',
    b'ANbf': 'Pandaren Brewmaster:Breath of Fire',
    b'ANdb': 'Pandaren Brewmaster:Drunken Brawler',
    b'ANdh': 'Pandaren Brewmaster:Drunken Haze',
    b'ANef': 'Pandaren Brewmaster:Storm Earth and Fire',
    b'ANdr': 'Dark Ranger:Life Drain',
    b'ANsi': 'Dark Ranger:Silence',
    b'ANba': 'Dark Ranger:Black Arrow',
    b'ANch': 'Dark Ranger:Charm',
    b'ANms': 'Naga Sea Witch:Mana Shield',
    b'ANfa': 'Naga Sea Witch:Frost Arrows',
    b'ANfl': 'Naga Sea Witch:Forked Lightning',
    b'ANto': 'Naga Sea Witch:Tornado',
    b'ANrf': 'Pit Lord:Rain of Fire',
    b'ANca': 'Pit Lord:Cleaving Attack',
    b'ANht': 'Pit Lord:Howl of Terror',
    b'ANdo': 'Pit Lord:Doom',
    b'ANsg': 'Beastmaster:Summon Bear',
    b'ANsq': 'Beastmaster:Summon Quilbeast',
    b'ANsw': 'Beastmaster:Summon Hawk',
    b'ANst': 'Beastmaster:Stampede',
    b'ANeg': 'Goblin Tinker:Engineering Upgrade',
    b'ANcs': 'Goblin Tinker:Cluster Rockets',
    b'ANc1': 'Goblin Tinker:Cluster Rockets 1',
    b'ANc2': 'Goblin Tinker:Cluster Rockets 2',
    b'ANc3': 'Goblin Tinker:Cluster Rockets 3',
    b'ANsy': 'Goblin Tinker:Pocket Factory',
    b'ANs1': 'Goblin Tinker:Pocket Factory 1',
    b'ANs2': 'Goblin Tinker:Pocket Factory 2',
    b'ANs3': 'Goblin Tinker:Pocket Factory 3',
    b'ANrg': 'Goblin Tinker:Robo-Goblin',
    b'ANg1': 'Goblin Tinker:Robo-Goblin 1',
    b'ANg2': 'Goblin Tinker:Robo-Goblin 2',
    b'ANg3': 'Goblin Tinker:Robo-Goblin 3',
    b'ANic': 'Firelord:Incinerate',
    b'ANia': 'Firelord:Incinerate',
    b'ANso': 'Firelord:Soul Burn',
    b'ANlm': 'Firelord:Summon Lava Spawn',
    b'ANvc': 'Firelord:Volcano',
    b'ANhs': 'Goblin Alchemist:Healing Spray',
    b'ANab': 'Goblin Alchemist:Acid Bomb',
    b'ANcr': 'Goblin Alchemist:Chemical Rage',
    b'ANtm': 'Goblin Alchemist:Transmute',
    # numeric item id
    b'\x03\x00\x0D\x00': 'Rightclick',
    b'\x04\x00\x0D\x00': 'Stop',
    b'\x08\x00\x0D\x00': 'Cancel',
    b'\x0C\x00\x0D\x00': 'Set rally point',
    b'\x0F\x00\x0D\x00': 'Attack',
    b'\x10\x00\x0D\x00': 'Attack ground',
    b'\x12\x00\x0D\x00': 'Move unit',
    b'\x16\x00\x0D\x00': 'Patrol',
    b'\x19\x00\x0D\x00': 'Hold position',
    b'\x21\x00\x0D\x00': 'Give item',
    b'\x22\x00\x0D\x00': 'Swap item place 7 (slot of item to swap with!)',
    b'\x23\x00\x0D\x00': 'Swap item place 8',
    b'\x24\x00\x0D\x00': 'Swap item place 4',
    b'\x25\x00\x0D\x00': 'Swap item place 5',
    b'\x26\x00\x0D\x00': 'Swap item place 1',
    b'\x27\x00\x0D\x00': 'Swap item place 2',
    b'\x28\x00\x0D\x00': 'Use item place 7',
    b'\x29\x00\x0D\x00': 'Use item place 8',
    b'\x2A\x00\x0D\x00': 'Use item place 4',
    b'\x2B\x00\x0D\x00': 'Use item place 5',
    b'\x2C\x00\x0D\x00': 'Use item place 1',
    b'\x2D\x00\x0D\x00': 'Use item place 2',
    b'\x31\x00\x0D\x00': 'Return with resources',
    b'\x32\x00\x0D\x00': 'Mine',
    b'\x37\x00\x0D\x00': 'Use ability: reveal area (N goblin laboratory)',
    b'\x38\x00\x0D\x00': 'Use ability: repair (HU peasant, Orc peon)',
    b'\x39\x00\x0D\x00': 'Enable autocast: repair (HU peasant, Orc peon)',
    b'\x3A\x00\x0D\x00': 'Disable autocast: repair (HU peasant, Orc peon)',
    b'\x3B\x00\x0D\x00': 'Revive hero (first of 1 or more dead heros)',
    b'\x3C\x00\x0D\x00': 'Revive hero (second of 2 or more dead heros)',
    b'\x3D\x00\x0D\x00': 'Revive hero (third of 3 or more dead heros)',
    b'\x3E\x00\x0D\x00': 'Revive hero (fourth of 4 or more dead heros)',
    b'\x3F\x00\x0D\x00': 'Revive hero (fifth of 5 dead heros)',
    b'\x48\x00\x0D\x00': 'Use ability: kaboom (Goblin sapper)',
    b'\x49\x00\x0D\x00': 'Enable autocast: kaboom (Goblin sapper)',
    b'\x4A\x00\x0D\x00': 'Disable autocast: kaboom (Goblin sapper)',
    b'\x4E\x00\x0D\x00': 'Load unit (NE mine/Zepellin)',
    b'\x4F\x00\x0D\x00': 'Remove single unit (click unit) (NE mine/Zepellin)',
    b'\x50\x00\x0D\x00': 'Unload all units (NE mine/Zepellin)',
    b'\x51\x00\x0D\x00': 'All wisp exit mine (button) (NE gold mine)',
    b'\x53\x00\x0D\x00': 'Enable autocast: load corpses (UD: meat wagon)',
    b'\x54\x00\x0D\x00': 'Disable autocast: load corpses (UD: meat wagon)',
    b'\x55\x00\x0D\x00': 'Use ability: load corpses (UD: meat wagon)',
    b'\x56\x00\x0D\x00': 'Use ability: unload corpses (UD: meat wagon)',
    b'\x57\x00\x0D\x00': 'Use ability: enable defend (HU footman)',
    b'\x58\x00\x0D\x00': 'Use ability: disable defend (HU footman)',
    b'\x59\x00\x0D\x00': 'Use ability: area dispell (Hu priest)',
    b'\x5C\x00\x0D\x00': 'Use ability: flare (Hu Mortar team)',
    b'\x5F\x00\x0D\x00': 'Use ability: heal (Hu priest)',
    b'\x60\x00\x0D\x00': 'Enable autocast heal (Hu priest)',
    b'\x61\x00\x0D\x00': 'Disable autocast heal (Hu priest)',
    b'\x62\x00\x0D\x00': 'Use ability: inner fire (Hu priest)',
    b'\x63\x00\x0D\x00': 'Enable autocast inner fire (Hu priest)',
    b'\x64\x00\x0D\x00': 'Disable autocast inner fire (Hu priest)',
    b'\x65\x00\x0D\x00': 'Use ability: invisibility (Hu sorcress)',
    b'\x68\x00\x0D\x00': 'Use ability: call to arms (Hu peasant)',
    b'\x69\x00\x0D\x00': 'Use ability: return to work (Hu militia)',
    b'\x6A\x00\x0D\x00': 'Use ability: polymorph (Hu sorcress)',
    b'\x6B\x00\x0D\x00': 'Use ability: slow (Hu sorcress)',
    b'\x6C\x00\x0D\x00': 'Enable autocast slow (Hu sorcress)',
    b'\x6D\x00\x0D\x00': 'Disable autocast slow (Hu sorcress)',
    b'\x72\x00\x0D\x00': 'Call to arms (Hu townhall)',
    b'\x73\x00\x0D\x00': 'Return to work (Hu townhall)',
    b'\x76\x00\x0D\x00': 'Use ability: avatar (Hu Mountain King ultimate)',
    b'\x79\x00\x0D\x00': 'Use ability: blizzard (Hu Archmage)',
    b'\x7A\x00\x0D\x00': 'Use ability: divine shield (Hu Paladin)',
    b'\x7B\x00\x0D\x00': 'Use ability: divine shield - turn off(Hu Paladin)',
    b'\x7C\x00\x0D\x00': 'Use ability: holy light (Hu Paladin)',
    b'\x7D\x00\x0D\x00': 'Use ability: mass teleportation (Hu Archmage)',
    b'\x7E\x00\x0D\x00': 'Use ability: revive (Hu Paladin ultimate)',
    b'\x7F\x00\x0D\x00': 'Use ability: storm bolt (Hu Mountain King)',
    b'\x80\x00\x0D\x00': 'Use ability: clap (Hu Mountain King)',
    b'\x81\x00\x0D\x00': 'Use ability: summon water elemental (Hu Archmage)',
    b'\x83\x00\x0D\x00': 'Peons into combat positions (Orc Burrow)',
    b'\x84\x00\x0D\x00': 'Berserk (Orc troll berserker)',
    b'\x85\x00\x0D\x00': 'Use ability: bloodlust (Orc Shaman)',
    b'\x86\x00\x0D\x00': 'Enable autocast bloodlust (Orc Shaman)',
    b'\x87\x00\x0D\x00': 'Disable autocast bloodlust (Orc Shaman)',
    b'\x88\x00\x0D\x00': 'Use ability: devour (Orc Kodo beast)',
    b'\x89\x00\x0D\x00': 'Use ability: sentry ward (Orc Witch Doctor)',
    b'\x8A\x00\x0D\x00': 'Use ability: entangle (Orc Raider)',
    b'\x8D\x00\x0D\x00': 'Use ability: healing ward (Orc Witch Doctor)',
    b'\x8E\x00\x0D\x00': 'Use ability: lightning shield (Orc Shaman)',
    b'\x8F\x00\x0D\x00': 'Use ability: purge (Orc Shaman)',
    b'\x91\x00\x0D\x00': 'Return to work (Orc Burrow)',
    b'\x92\x00\x0D\x00': 'Use ability: stasis trap (Orc Witch Doctor)',
    b'\x97\x00\x0D\x00': 'Use ability: chain lightning (Orc Farseer)',
    b'\x99\x00\x0D\x00': 'Use ability: earthquake (Orc Farseer ultimate)',
    b'\x9A\x00\x0D\x00': 'Use ability: farsight (Orc Farseer)',
    b'\x9B\x00\x0D\x00': 'Use ability: mirror image (Orc Blademaster)',
    b'\x9D\x00\x0D\x00': 'Use ability: shockwave (Orc Tauren Chieftain)',
    b'\x9E\x00\x0D\x00': 'Use ability: shadow wolves (Orc Farseer)',
    b'\x9F\x00\x0D\x00': 'Use ability: war stomp (Orc Tauren Chieftain)',
    b'\xA0\x00\x0D\x00': 'Use ability: blade storm (Orc Blademaster ultimate)',
    b'\xA1\x00\x0D\x00': 'Use ability: wind walk (Orc Blademaster)',
    b'\xA3\x00\x0D\x00': 'Use ability: shadowmeld (NE females)',
    b'\xA4\x00\x0D\x00': 'Use ability: dispell magic (NE Dryad)',
    b'\xA5\x00\x0D\x00': 'Enable autocast: dispell magic (NE Dryad)',
    b'\xA6\x00\x0D\x00': 'Disable autocast: dispell magic (NE Dryad)',
    b'\xAA\x00\x0D\x00': 'Use ability: transform: DotC -> bear (NE DotC)',
    b'\xAB\x00\x0D\x00': 'Use ability: transform: bear -> DotC (NE DotC)',
    b'\xAE\x00\x0D\x00': 'Use ability: pick up archer (NE hippogryph)',
    b'\xAF\x00\x0D\x00': 'Use ability: mount hippogryph (NE archer)',
    b'\xB0\x00\x0D\x00': 'Use ability: cyclone (NE DotT)',
    b'\xB1\x00\x0D\x00': 'Use ability: detonate (NE Wisp)',
    b'\xB2\x00\x0D\x00': 'Use ability: eat tree (NE Ancient)',
    b'\xB3\x00\x0D\x00': 'Use ability: entangle goldmine (NE Tree of Life)',
    b'\xB5\x00\x0D\x00': 'Use ability: feary fire (NE DotT)',
    b'\xB6\x00\x0D\x00': 'Enable autocast: feary fire (NE DotT)',
    b'\xB7\x00\x0D\x00': 'Disable autocast: feary fire (NE DotT)',
    b'\xBB\x00\x0D\x00': 'Use ability: transform into crow form (NE DotT)',
    b'\xBC\x00\x0D\x00': 'Use ability: transform back from crow form (NE DotT)',
    b'\xBD\x00\x0D\x00': 'Use ability: replenish life/mana (NE Moon well)',
    b'\xBE\x00\x0D\x00': 'Enable autocast: replenish life/mana (NE Moon well)',
    b'\xBF\x00\x0D\x00': 'Disable autocast: replenish life/mana (NE Moon well)',
    b'\xC0\x00\x0D\x00': 'Use ability: rejuvenation (NE DotC)',
    b'\xC1\x00\x0D\x00': 'Use ability: renew (repair) (NE Wisp)',
    b'\xC2\x00\x0D\x00': 'Enable autocast: renew (repair) (NE Wisp)',
    b'\xC3\x00\x0D\x00': 'Disable autocast: renew (repair) (NE Wisp)',
    b'\xC4\x00\x0D\x00': 'Use ability: roar (NE DotC)',
    b'\xC5\x00\x0D\x00': 'Use ability: root (NE Ancient)',
    b'\xC6\x00\x0D\x00': 'Use ability: uproot (NE Ancient)',
    b'\xCB\x00\x0D\x00': 'Use ability: entangling roots (NE KotG)',
    b'\xCD\x00\x0D\x00': 'Use ability: searing arrow (NE PotM)',
    b'\xCE\x00\x0D\x00': 'Enable autocast: searing arrow (NE PotM)',
    b'\xCF\x01\x0D\x00': 'Disable autocast: searing arrow (NE PotM)',
    b'\xD0\x00\x0D\x00': 'Use ability: summon treants (NE KotG)',
    b'\xD1\x00\x0D\x00': 'Use ability: immolation ON (NE Daemon Hunter)',
    b'\xD2\x00\x0D\x00': 'Use ability: immolation OFF (NE Daemon Hunter)',
    b'\xD3\x00\x0D\x00': 'Use ability: manaburn (NE Daemon Hunter)',
    b'\xD4\x00\x0D\x00': 'Use ability: metamorphosis ((NE DH ultimate)',
    b'\xD5\x00\x0D\x00': 'Use ability: scout owl (NE PotM)',
    b'\xD6\x00\x0D\x00': 'Use ability: sentinel (NE huntress)',
    b'\xD7\x00\x0D\x00': 'Use ability: starfall (NE PotM ultimate)',
    b'\xD8\x00\x0D\x00': 'Use ability: tranquility (NE KotG ultimate)',
    b'\xDA\x00\x0D\x00': 'Use ability: anti magic shell (UD Banshee)',
    b'\xDC\x00\x0D\x00': 'Use ability: cannibalize (UD Ghoul)',
    b'\xDD\x00\x0D\x00': 'Use ability: cripple (UD Necromancer)',
    b'\xDE\x00\x0D\x00': 'Use ability: curse (UD Banshee)',
    b'\xDF\x00\x0D\x00': 'Enable autocast: curse (UD Banshee)',
    b'\xE0\x00\x0D\x00': 'Disable autocast: curse (UD Banshee)',
    b'\xE4\x00\x0D\x00': 'Use ability: possession (UD Banshee)',
    b'\xE6\x00\x0D\x00': 'Enable autocast: raise skeletons (UD Necromancer)',
    b'\xE7\x00\x0D\x00': 'Disable autocast: raise skeletons (UD Necromancer)',
    b'\xE8\x00\x0D\x00': 'Use ability: raise skeletons (UD Necromancer)',
    b'\xE9\x00\x0D\x00': 'Use ability: sacrifice (UD Acolyte button)',
    b'\xEA\x00\x0D\x00': 'Use ability: restore (repair) (UD Acolyte)',
    b'\xEB\x00\x0D\x00': 'Enable autocast: restore (repair) (UD Acolyte)',
    b'\xEC\x00\x0D\x00': 'Disable autocast: restore (repair) (UD Acolyte)',
    b'\xED\x00\x0D\x00': 'Use ability: sacrifice (Sacrificial Pit\'s button)',
    b'\xEE\x00\x0D\x00': 'Transform: gargoyle -> stone (UD Gargoyle)',
    b'\xEF\x00\x0D\x00': 'Transform: stone -> gargoyle (UD Gargoyle)',
    b'\xF1\x00\x0D\x00': 'Use ability: unholy frenzy (UD Necromancer)',
    b'\xF2\x00\x0D\x00': 'Use ability: unsummon (UD Acolyte)',
    b'\xF3\x00\x0D\x00': 'Use ability: web (UD Crypt fiend)',
    b'\xF4\x00\x0D\x00': 'Enable autocast: web (UD Crypt fiend)',
    b'\xF5\x00\x0D\x00': 'Disable autocast: web (UD Crypt fiend)',
    b'\xF9\x00\x0D\x00': 'Use ability: animate dead (UD DeathKnight ultimate)',
    b'\xFA\x00\x0D\x00': 'Use ability: swarm (UD Dreadlord)',
    b'\xFB\x00\x0D\x00': 'Use ability: dark ritual (UD Lich)',
    b'\xFD\x00\x0D\x00': 'Use ability: death and decay (UD Lich ultimate)',
    b'\xFE\x00\x0D\x00': 'Use ability: death coil (UD DeathKnight)',
    b'\xFF\x00\x0D\x00': 'Use ability: death pact (UD DeathKnight)',
    b'\x00\x01\x0D\x00': 'Use ability: Inferno (UD Dreadlord ultimate)',
    b'\x01\x01\x0D\x00': 'Use ability: frost armor (UD Lich)',
    b'\x02\x01\x0D\x00': 'Use ability: frost nova (UD Lich)',
    b'\x03\x01\x0D\x00': 'Use ability: sleep (UD Dreadlord)',
    b'\x04\x01\x0D\x00': 'Use ability: dark conversion (N Malganis)',
    b'\x05\x01\x0D\x00': 'Use ability: Dark portal (N Archimonde)',
    b'\x06\x01\x0D\x00': 'Use ability: Finger of death (N Archimonde)',
    b'\x07\x01\x0D\x00': 'Use ability: Firebolt (N Warlock)',
    b'\x0E\x01\x0D\x00': 'Use ability: Rain of Fire (Pit Lord)',
    b'\x12\x01\x0D\x00': 'Use ability: soul preservation (N Malganis)',
    b'\x13\x01\x0D\x00': 'Use ability: cold arrows (N Sylvana)',
    b'\x14\x01\x0D\x00': 'Enable autocast: cold arrows (N Sylvana)',
    b'\x15\x01\x0D\x00': 'Disable autocast: cold arrows (N Sylvana)',
    b'\x16\x01\x0D\x00': 'Use ability: animate dead (N Satyr Hellcaller)',
    b'\x17\x01\x0D\x00': 'Use ability: devour (N Storm Wyrm)',
    b'\x18\x01\x0D\x00': 'Use ability: heal (N Troll Shadowpriest)',
    b'\x19\x01\x0D\x00': 'Enable autocast: heal (N Troll Shadowpriest)',
    b'\x1A\x01\x0D\x00': 'Disable autocast: heal (N Troll Shadowpriest)',
    b'\x1C\x01\x0D\x00': 'Use ability: creep storm bolt (N Stone Golem)',
    b'\x1D\x01\x0D\x00': 'Use ability: creep thunder clap (N Granit Golem)',
    b'\x2E\x01\x0D\x00': 'Use ability: reveal (HU Arcane Tower)',
    b'\xE9\x01\x0D\x00': 'Enable autocast frost armor (UD Lich)',
    b'\xEA\x01\x0D\x00': 'Enable/disable autocast frost armor (UD Lich)',
    b'\xEB\x01\x0D\x00': 'Disable autocast frost armor (UD Lich)',
    b'\xEE\x01\x0D\x00': 'Revive first dead hero on tavern',
    b'\xEF\x01\x0D\x00': 'Revive second dead hero on tavern',
    b'\xF0\x01\x0D\x00': 'Revive third dead hero on tavern',
    b'\xF1\x01\x0D\x00': 'Revive 4th dead hero on tavern',
    b'\xF2\x01\x0D\x00': 'Revive 5th dead hero on tavern',
    b'\xF9\x01\x0D\x00': 'Cloud (HU dragonhawk rider)',
    b'\xFA\x01\x0D\x00': 'Control Magic (HU spell breaker)',
    b'\x00\x02\x0D\x00': 'Aerial Shackles (HU dragonhawk rider)',
    b'\x03\x02\x0D\x00': 'Spell Steal (HU spell breaker)',
    b'\x04\x02\x0D\x00': 'Enable autocast: Spell Steal (HU spell breaker)',
    b'\x05\x02\x0D\x00': 'Disable autocast: Spell Steal (HU spell breaker)',
    b'\x06\x02\x0D\x00': 'Banish (HU blood mage)',
    b'\x07\x02\x0D\x00': 'Siphon Mana (HU blood mage / Dark Ranger)',
    b'\x08\x02\x0D\x00': 'Flame Strike (HU blood mage)',
    b'\x09\x02\x0D\x00': 'Phoenix (HU blood mage ultimate)',
    b'\x0A\x02\x0D\x00': 'Ancestral Spirit (Orc spirit walker)',
    b'\x0D\x02\x0D\x00': 'Transform to Corporeal Form (Orc spirit walker)',
    b'\x0E\x02\x0D\x00': 'Transform to Ethereal Form (Orc spirit walker)',
    b'\x13\x02\x0D\x00': 'Spirit link (Orc spirit walker)',
    b'\x14\x02\x0D\x00': 'Unstable Concoction (Orc troll batrider)',
    b'\x15\x02\x0D\x00': 'Healing Wave (Orc shadow hunter)',
    b'\x16\x02\x0D\x00': 'Hex (Orc shadow hunter)',
    b'\x17\x02\x0D\x00': 'Big Bad Voodoo (Orc shadow hunter ultimate)',
    b'\x18\x02\x0D\x00': 'Serpent Ward (Orc shadow hunter)',
    b'\x1C\x02\x0D\x00': 'Build Hippogryph Rider (NE archer / hippogryph)',
    b'\x1D\x02\x0D\x00': 'Separate Archer (NE hippograph raider)',
    b'\x1F\x02\x0D\x00': 'War Club (NE mountain giant)',
    b'\x20\x02\x0D\x00': 'Mana Flare (NE faerie dragon)',
    b'\x21\x02\x0D\x00': 'Mana Flare (NE faerie dragon)',
    b'\x22\x02\x0D\x00': 'Phase Shift (NE faerie dragon)',
    b'\x23\x02\x0D\x00': 'Enable autocast: Phase Shift (NE faerie dragon)',
    b'\x24\x02\x0D\x00': 'Disable autocast: Phase Shift (NE faerie dragon)',
    b'\x28\x02\x0D\x00': 'Taunt (NE mountain giant)',
    b'\x2A\x02\x0D\x00': 'Enable autocast: Spirit of Vengeance (NE vengeance ultimate)',
    b'\x2B\x02\x0D\x00': 'Disable autocast: Spirit of Vengeance (NE vengeance ultimate)',
    b'\x2C\x02\x0D\x00': 'Spirit of Vengeance (NE vengeance ultimate)',
    b'\x2D\x02\x0D\x00': 'Blink (NE warden)',
    b'\x2E\x02\x0D\x00': 'Fan of Knives (NE warden)',
    b'\x2F\x02\x0D\x00': 'Shadow Strike (NE warden)',
    b'\x30\x02\x0D\x00': 'Vengeance (NE warden ultimate)',
    b'\x31\x02\x0D\x00': 'Absorb Mana (UD destroyer)',
    b'\x33\x02\x0D\x00': 'Morph to Destroyer (UD obsidian statue)',
    b'\x35\x02\x0D\x00': 'Burrow (UD crypt fiend / carrion beetle)',
    b'\x36\x02\x0D\x00': 'Unburrow (UD crypt fiend / carrion beetle)',
    b'\x38\x02\x0D\x00': 'Devour Magic (UD destroyer)',
    b'\x3B\x02\x0D\x00': 'Orb of Annihilation (UD destroyer)',
    b'\x3C\x02\x0D\x00': 'Enable autocast: Orb of Annihilation (UD destroyer)',
    b'\x3D\x02\x0D\x00': 'Disable autocast: Orb of Annihilation (UD destroyer)',
    b'\x41\x02\x0D\x00': 'Essence of Blight (UD obsidian statue)',
    b'\x42\x02\x0D\x00': 'Enable autocast: Essence of Blight (UD obsidian statue)',
    b'\x43\x02\x0D\x00': 'Disable autocast: Essence of Blight (UD obsidian statue)',
    b'\x44\x02\x0D\x00': 'Spirit Touch (UD obsidian statue)',
    b'\x45\x02\x0D\x00': 'Enable autocast: Spirit Touch (UD obsidian statue)',
    b'\x46\x02\x0D\x00': 'Disable autocast: Spirit Touch (UD obsidian statue)',
    b'\x48\x02\x0D\x00': 'Enable autocast: Carrion Beetles (UD crypt lord)',
    b'\x49\x02\x0D\x00': 'Disable autocast: Carrion Beetles (UD crypt lord)',
    b'\x4A\x02\x0D\x00': 'Carrion Beetle (UD crypt lord)',
    b'\x4B\x02\x0D\x00': 'Impale (UD crypt lord)',
    b'\x4C\x02\x0D\x00': 'Locust Swarm (UD crypt lord ultimate)',
    b'\x51\x02\x0D\x00': 'Frenzy (beastmasters quilbeast)',
    b'\x52\x02\x0D\x00': 'Enable autocast: Frenzy (beastmasters quilbeast)',
    b'\x53\x02\x0D\x00': 'Disable autocast: Frenzy (beastmasters quilbeast)',
    b'\x56\x02\x0D\x00': 'Change Shop Buyer',
    b'\x61\x02\x0D\x00': 'Black Arrow (Dark Ranger)',
    b'\x62\x02\x0D\x00': 'Enable autocast: Black Arrow (Dark Ranger)',
    b'\x63\x02\x0D\x00': 'Disable autocast: Black Arrow (Dark Ranger)',
    b'\x64\x02\x0D\x00': 'Breath of Fire (Pandaren Brewmaster)',
    b'\x65\x02\x0D\x00': 'Charm (Dark Ranger ultimate)',
    b'\x67\x02\x0D\x00': 'Doom (Pit Lord ultimate)',
    b'\x69\x02\x0D\x00': 'Drunken Haze (Pandaren Brewmaster)',
    b'\x6A\x02\x0D\x00': 'Storm, Earth and Fire (Pandaren ultimate)',
    b'\x6B\x02\x0D\x00': 'Forked Lightning (Naga Sea Witch)',
    b'\x6C\x02\x0D\x00': 'Howl of Terror (Pit Lord)',
    b'\x6D\x02\x0D\x00': 'Mana Shield (Naga Sea Witch)',
    b'\x6E\x02\x0D\x00': 'Mana Shield (Naga Sea Witch)',
    b'\x70\x02\x0D\x00': 'Silence (Dark Ranger)',
    b'\x71\x02\x0D\x00': 'Stampede (Beastmaster ultimate)',
    b'\x72\x02\x0D\x00': 'Summon Bear (Beastmaster)',
    b'\x73\x02\x0D\x00': 'Summon Quilbeast (Beastmaster)',
    b'\x74\x02\x0D\x00': 'Summon Hawk (Beastmaster)',
    b'\x75\x02\x0D\x00': 'Tornado (Naga Sea Witch ultimate)',
    b'\x76\x02\x0D\x00': 'Summon Prawn (N Makrura Snapper)',
    b'\xAC\x02\x0D\x00': 'Cluster Rockets (Goblin Tinker)',
    b'\xB0\x02\x0D\x00': 'Robo-Goblin (Goblin Tinker ultimate)',
    b'\xB1\x02\x0D\x00': 'Revert to Tinker (Goblin Tinker)',
    b'\xB2\x02\x0D\x00': 'Pocket Factory (Goblin Tinker)',
    b'\xB6\x02\x0D\x00': 'Acid Bomb (Goblin Alchemist)',
    b'\xB7\x02\x0D\x00': 'Chemical Rage (Goblin Alchemist)',
    b'\xB8\x02\x0D\x00': 'Healing Spray (Goblin Alchemist)',
    b'\xB9\x02\x0D\x00': 'Transmute (Goblin Alchemist)',
    b'\xBB\x02\x0D\x00': 'Summon Lava Spawn (Fire Lord)',
    b'\xBC\x02\x0D\x00': 'Soulburn (Fire Lord)',
    b'\xBD\x02\x0D\x00': 'Volcano (Fire Lord)',
    b'\xBE\x02\x0D\x00': 'Incinerate (Fire Lord)',
    b'\xBF\x02\x0D\x00': 'Enable autocast: Incinerate (Fire Lord)',
    b'\xC0\x02\x0D\x00': 'Disable autocast: Incinerate (Fire Lord)',
    b'\xFF\xFF\xFF\xFF': 'Ground',
}
ABILITY_FLAGS = {
    0x0001: 'queue command',
    0x0002: 'apply to all units in subgroup',
    0x0004: 'area effect',
    0x0008: 'group command',
    0x0010: 'move group without formation',
    0x0020: None,
    0x0040: 'subgroup command',
    0x0100: 'autocast enabled/disabled',
}
ITEMS_TO_RACE = {
    b'emow': 'nightelf',  # Moon Well
    b'etoa': 'nightelf',  # Tree of Ages
    b'etol': 'nightelf',  # Tree of Life
    b'ewsp': 'nightelf',  # Wisp
    b'hpea': 'human',  # Peasant
    b'htow': 'human',  # Town Hall
    b'otrb': 'orc',  # Burrow
    b'ogre': 'orc',  # Great Hall
    b'opeo': 'orc',  # Peon
    b'uaco': 'undead',  # Acolyte
    b'uzig': 'undead',  # Ziggurat
    b'unpl': 'undead',  # Necropolis
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
        if custom_or_ladder != 0x08:  # custom
            n += custom_or_ladder
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

class ReforgedPlayerMetadata(namedtuple('ReforgedPlayerMetadata', 
                                         ['id','name','clan', 'raw', 'size'])):
    def __new__(cls, id=-1, name='', clan='', raw=b'', size=0):
        self = super(ReforgedPlayerMetadata, cls).__new__(cls, id=id, name=name, 
                                                            clan=clan, raw=raw, size=size)
        return self
        
    @classmethod
    def from_raw(cls, data):
        n = 0
        kw = {}

        kw['size'] = b2i(data[n])
        n += 2
        kw['id'] = b2i(data[n])
        n += 2
        int_name_length = b2i(data[n])
        n += 1
        kw['name'] = fixedlengthstr(data[n:], int_name_length)
        n = n + int_name_length + 1
        int_clan_length = b2i(data[n])
        n += 1
        kw['clan'] = fixedlengthstr(data[n:], int_clan_length)
        n = n + int_clan_length + 1
        int_extra_length = b2i(data[n])
        n += 1
        kw['raw'] = data[:kw['size']]
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
              'color': COLORS[b2i(data[5])] if len(COLORS) > b2i(data[5]) else 'other',
              'race': RACES.get(b2i(data[6] & 0x3F), 'none'),
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

    apm = False

    def __init__(self, f):
        self.f = f
        self.time = f.clock

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

    apm = False

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

    apm = False

    remote_results = {
        0x01: 'left',
        0x07: 'left',
        0x08: 'lost',
        0x09: 'won',
        0x0A: 'draw',
        0x0B: 'left',
        0x0D: 'left',
        }

    local_not_last_results = {
        0x01: 'disconnected',
        0x07: 'left',
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

    apm = False

    def __init__(self, f, mode, secs):
        super(Countdown, self).__init__(f)
        self.mode = mode
        self.secs = secs

    def __str__(self):
        t = self.strtime()
        rtn = "[{t}] Game countdown {mode}, {m:02}:{s:02} left"
        return rtn.format(t=t, mode=self.mode, m=int(self.secs/60), s=self.secs%60)

class Action(Event):

    le = -1
    id = -1
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(Action, self).__init__(f)
        self.player_id = player_id

    def __str__(self):
        t = self.strtime()
        p = self.f.player_name(self.player_id)
        rtn = "[{t}] <{c}> {p}"
        return rtn.format(t=t, c=self.__class__.__name__, p=p)

    def obj(self, o):
        if o == b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF':
            return 'Ground'
        return 'Object#{0}'.format(b2i(o))

class Pause(Action):

    id = 0x01
    apm = False

    def __init__(self, f, player_id, action_block):
        super(Pause, self).__init__(f, player_id, action_block)

class Resume(Action):

    id = 0x02
    apm = False

    def __init__(self, f, player_id, action_block):
        super(Resume, self).__init__(f, player_id, action_block)

class SetGameSpeed(Action):

    id = 0x03
    size = 2
    apm = False

    def __init__(self, f, player_id, action_block):
        super(SetGameSpeed, self).__init__(f, player_id, action_block)
        self.speed = b2i(action_block[1])

    def __str__(self):
        s = super(SetGameSpeed, self).__str__()
        return '{0} - {1}'.format(s, SPEEDS[self.speed])

class IncreaseGameSpeed(Action):

    id = 0x04
    apm = False

    def __init__(self, f, player_id, action_block):
        super(IncreaseGameSpeed, self).__init__(f, player_id, action_block)

class DecreaseGameSpeed(Action):

    id = 0x05
    apm = False

    def __init__(self, f, player_id, action_block):
        super(DecreaseGameSpeed, self).__init__(f, player_id, action_block)

class SaveGame(Action):

    id = 0x06
    size = None
    apm = False

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
    apm = False

    def __init__(self, f, player_id, action_block):
        super(SaveGameFinished, self).__init__(f, player_id, action_block)

class Ability(Action):

    id = 0x10
    apm = True

    def __init__(self, f, player_id, action_block):
        super(Ability, self).__init__(f, player_id, action_block)
        offset = 1
        o = 1 if f.build_num < BUILD_1_13 else WORD
        self.flags = b2i(action_block[offset:offset+o])
        offset += o
        self.ability = ability = action_block[offset:offset+DWORD]
        if ability[-2:] != NUMERIC_ITEM:
            self.ability = ability[::-1]
        offset += DWORD
        offset += 2 * DWORD if f.build_num >= BUILD_1_07 else 0
        self.size = offset

    def __str__(self):
        s = super(Ability, self).__str__()
        aflgs = ABILITY_FLAGS.get(self.flags, None)
        astr = '' if aflgs is None else ' [{0}]'.format(aflgs)
        return '{0} - {1}{2}'.format(s, ITEMS.get(self.ability, self.ability), astr)

class AbilityPosition(Ability):

    id = 0x11
    apm = True

    def __init__(self, f, player_id, action_block):
        super(AbilityPosition, self).__init__(f, player_id, action_block)
        offset = self.size
        x = b2f(action_block[offset:offset+DWORD])
        offset += DWORD
        y = b2f(action_block[offset:offset+DWORD])
        offset += DWORD
        self.loc = (x, y)
        self.size = offset

    def __str__(self):
        s = super(AbilityPosition, self).__str__()
        return '{0} at ({1:.3%}, {2:.3%})'.format(s, self.loc[0]/MAXPOS,
                                                     self.loc[1]/MAXPOS)

class AbilityPositionObject(AbilityPosition):

    id = 0x12
    apm = True

    def __init__(self, f, player_id, action_block):
        super(AbilityPositionObject, self).__init__(f, player_id, action_block)
        offset = self.size
        self.object = action_block[offset:offset+2*DWORD]
        offset += 2*DWORD
        self.size = offset

    def _super_str(self):
        return super(AbilityPositionObject, self).__str__()

    def __str__(self):
        s = super(AbilityPositionObject, self).__str__()
        return '{0} {1}'.format(s, self.obj(self.object))

class GiveItem(AbilityPositionObject):

    id = 0x13
    apm = True

    def __init__(self, f, player_id, action_block):
        super(GiveItem, self).__init__(f, player_id, action_block)
        offset = self.size
        self.item = action_block[offset:offset+2*DWORD]
        offset += 2*DWORD
        self.size = offset

    def __str__(self):
        s = super(GiveItem, self)._super_str()
        return '{0} {1} -> {2}'.format(s, self.obj(self.item),
                                          self.obj(self.object))

class DoubleAbility(AbilityPosition):

    id = 0x14
    apm = True

    def __init__(self, f, player_id, action_block):
        super(DoubleAbility, self).__init__(f, player_id, action_block)
        self.ability1 = self.ability
        self.loc1 = self.loc
        offset = self.size
        self.ability2 = ability2 = action_block[offset:offset+DWORD]
        offset += DWORD
        if ability2[-2:] != NUMERIC_ITEM:
            self.ability2 = ability2[::-1]
        offset += 9
        x2 = b2f(action_block[offset:offset+DWORD])
        offset += DWORD
        y2 = b2f(action_block[offset:offset+DWORD])
        offset += DWORD
        self.loc2 = (x2, y2)
        self.size = offset

    def __str__(self):
        s = super(DoubleAbility, self).__str__()
        loc2str = ''
        if self.loc1 != self.loc2:
            loc2str = ' at ({0:.3%}, {1:.3%})'.format(self.loc2[0]/MAXPOS,
                                                      self.loc2[1]/MAXPOS)
        return '{0} -> {1}{2}'.format(s, ITEMS.get(self.ability2, self.ability2),
                                      loc2str)

class ChangeSelection(Action):

    id = 0x16
    apm = True

    modes = {0x01: 'Select', 0x02: 'Deselect'}

    def __init__(self, f, player_id, action_block):
        super(ChangeSelection, self).__init__(f, player_id, action_block)
        self.mode = b2i(action_block[1])
        n = b2i(action_block[2:2+WORD])
        self.size = 4 + 8*n
        objs = action_block[4:]
        self.objects = [objs[i:i+8] for i in range(n)]
        self.calc_apm()

    def calc_apm(self):
        if self.mode == 0x02:
            return
        if len(self.f.events) == 0:
            return
        last = self.f.events[-1]
        if last.player_id != self.player_id:
            return
        if not isinstance(last, ChangeSelection):
            return
        if last.mode != 0x02:
            return
        self.apm = False

    def __str__(self):
        s = super(ChangeSelection, self).__str__()
        return '{0} {1} [{2}]'.format(s, self.modes[self.mode],
                                      ', '.join(map(self.obj, self.objects)))

class AssignGroupHotkey(Action):

    id = 0x17
    apm = True

    def __init__(self, f, player_id, action_block):
        super(AssignGroupHotkey, self).__init__(f, player_id, action_block)
        self.hotkey = (b2i(action_block[1]) + 1) % 10
        n = b2i(action_block[2:2+WORD])
        self.size = 4 + 8*n
        objs = action_block[4:]
        self.objects = [objs[i:i+8] for i in range(n)]

    def __str__(self):
        s = super(AssignGroupHotkey, self).__str__()
        return '{0} Assign Hotkey #{1} [{2}]'.format(s, self.hotkey,
            ', '.join(map(self.obj, self.objects)))

class SelectGroupHotkey(Action):

    id = 0x18
    size = 3
    apm = True

    def __init__(self, f, player_id, action_block):
        super(SelectGroupHotkey, self).__init__(f, player_id, action_block)
        self.hotkey = (b2i(action_block[1]) + 1) % 10

    def __str__(self):
        s = super(SelectGroupHotkey, self).__str__()
        return '{0} Select Hotkey #{1}'.format(s, self.hotkey)

class SelectSubgroup(Action):

    id = 0x19
    apm = False

    def __init__(self, f, player_id, action_block):
        super(SelectSubgroup, self).__init__(f, player_id, action_block)
        if f.build_num < BUILD_1_14B:
            self.size = 2
            self.subgroup = b2i(action_block[1])
            if self.subgroup != 0x00 and self.subgroup != 0xFF:
                self.apm = True
        else:
            self.size = 13
            offset = 1
            self.ability = ability = action_block[offset:offset+DWORD]
            offset += DWORD
            if ability[-2:] != NUMERIC_ITEM:
                self.ability = ability[::-1]
            self.object = action_block[offset:offset+2*DWORD]
            offset += 2*DWORD

    def __str__(self):
        s = super(SelectSubgroup, self).__str__()
        if self.f.build_num < BUILD_1_14B:
            return '{0} - #{1}'.format(s, self.subgroup)
        else:
            return '{0} - {1} {2}'.format(s,
                ITEMS.get(self.ability, self.ability), self.obj(self.object))

class PreSubselect(Action):

    id = 0x1A
    apm = False

    def __init__(self, f, player_id, action_block):
        super(PreSubselect, self).__init__(f, player_id, action_block)

class UnknownAction(Action):

    #  <=1.14b, >1.14b
    le = BUILD_1_14B
    id = (0x1A, 0x1B)
    size = 10
    apm = False

    def __init__(self, f, player_id, action_block):
        super(UnknownAction, self).__init__(f, player_id, action_block)

class SelectGroundItem(Action):

    #  <=1.14b, >1.14b
    le = BUILD_1_14B
    id = (0x1B, 0x1C)
    size = 10
    apm = True

    def __init__(self, f, player_id, action_block):
        super(SelectGroundItem, self).__init__(f, player_id, action_block)
        self.item = action_block[2:10]

    def __str__(self):
        s = super(SelectGroundItem, self).__str__()
        return '{0} - {1} '.format(s, self.obj(self.item))

class CancelHeroRevival(Action):

    #  <=1.14b, >1.14b
    le = BUILD_1_14B
    id = (0x1C, 0x1D)
    size = 9
    apm = True

    def __init__(self, f, player_id, action_block):
        super(CancelHeroRevival, self).__init__(f, player_id, action_block)
        self.hero = action_block[1:9]

    def __str__(self):
        s = super(CancelHeroRevival, self).__str__()
        return '{0} - {1} '.format(s, self.obj(self.hero))

class RemoveUnitFromBuildingQueue(Action):

    #  <=1.14b, >1.14b
    le = BUILD_1_14B
    id = (0x1D, 0x1E)
    size = 6
    apm = True

    def __init__(self, f, player_id, action_block):
        super(RemoveUnitFromBuildingQueue, self).__init__(f, player_id, action_block)
        self.pos = b2i(action_block[1])
        self.unit = unit = action_block[2:2+DWORD]
        if unit[-2:] != NUMERIC_ITEM:
            self.unit = unit[::-1]

    def __str__(self):
        s = super(RemoveUnitFromBuildingQueue, self).__str__()
        return '{0} - {1} at position #{2}'.format(s, ITEMS.get(self.unit, self.unit),
                                                   self.pos)

class RareUnknownAction(Action):

    id = 0x21
    size = 9
    apm = False

    def __init__(self, f, player_id, action_block):
        super(RareUnknownAction, self).__init__(f, player_id, action_block)

class TheDudeAbides(Action):

    id = 0x20
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(TheDudeAbides, self).__init__(f, player_id, action_block)

class SomebodySetUpUsTheBomb(Action):

    id = 0x22
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(SomebodySetUpUsTheBomb, self).__init__(f, player_id, action_block)

class WarpTen(Action):

    id = 0x23
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(WarpTen, self).__init__(f, player_id, action_block)

class IocainePowder(Action):

    id = 0x24
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(IocainePowder, self).__init__(f, player_id, action_block)

class PointBreak(Action):

    id = 0x25
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(PointBreak, self).__init__(f, player_id, action_block)

class WhosYourDaddy(Action):

    id = 0x26
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(WhosYourDaddy, self).__init__(f, player_id, action_block)

class KeyserSoze(Action):

    id = 0x27
    size = 6
    apm = False

    def __init__(self, f, player_id, action_block):
        super(KeyserSoze, self).__init__(f, player_id, action_block)
        self.gold = b2i(action_block[2:2+DWORD]) - 2**31

    def __str__(self):
        s = super(KeyserSoze, self).__str__()
        return '{0} - {1} gold'.format(s, self.gold)

class LeafitToMe(Action):

    id = 0x28
    size = 6
    apm = False

    def __init__(self, f, player_id, action_block):
        super(LeafitToMe, self).__init__(f, player_id, action_block)
        self.lumber = b2i(action_block[2:2+DWORD]) - 2**31

    def __str__(self):
        s = super(LeafitToMe, self).__str__()
        return '{0} - {1} lumber'.format(s, self.lumber)

class ThereIsNoSpoon(Action):

    id = 0x2
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(ThereIsNoSpoon, self).__init__(f, player_id, action_block)

class StrengthAndHonor(Action):

    id = 0x2A
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(StrengthAndHonor, self).__init__(f, player_id, action_block)

class ItVexesMe(Action):

    id = 0x2B
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(ItVexesMe, self).__init__(f, player_id, action_block)

class WhoIsJohnGalt(Action):

    id = 0x2C
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(WhoIsJohnGalt, self).__init__(f, player_id, action_block)

class GreedIsGood(Action):

    id = 0x2D
    size = 6
    apm = False

    def __init__(self, f, player_id, action_block):
        super(GreedIsGood, self).__init__(f, player_id, action_block)
        self.gold = self.lumber = b2i(action_block[2:2+DWORD]) - 2**31

    def __str__(self):
        s = super(GreedIsGood, self).__str__()
        return '{0} - {1} gold and {2} lumber'.format(s, self.gold, self.lumber)

class DayLightSavings(Action):

    id = 0x2E
    size = 5
    apm = False

    def __init__(self, f, player_id, action_block):
        super(DayLightSavings, self).__init__(f, player_id, action_block)
        self.time = struct.unpack('f', action_block[1:5])

class ISeeDeadPeople(Action):

    id = 0x2F
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(ISeeDeadPeople, self).__init__(f, player_id, action_block)

class Synergy(Action):

    id = 0x30
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(Synergy, self).__init__(f, player_id, action_block)

class SharpAndShiny(Action):

    id = 0x31
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(SharpAndShiny, self).__init__(f, player_id, action_block)

class AllYourBaseAreBelongToUs(Action):

    id = 0x32
    size = 1
    apm = False

    def __init__(self, f, player_id, action_block):
        super(AllYourBaseAreBelongToUs, self).__init__(f, player_id, action_block)

class ChangeAllyOptions(Action):

    id = 0x50
    size = 6
    apm = False

    def __init__(self, f, player_id, action_block):
        super(ChangeAllyOptions, self).__init__(f, player_id, action_block)
        self.ally_id = b2i(action_block[1])
        self.flags_bits = bits(b2i(action_block[2:4])) + bits(b2i(action_block[5:9]))

    def flagstr(self):
        fs = []
        b = self.flags_bits
        if all(b[:5]):
            fs.append('is allied')
        if b[5]:
            fs.append('shares vision')
        if b[6]:
            fs.append('shares unit control')
        svi = 10 if self.f.build_num >= BUILD_1_07 else 9

        if b[svi]:
            fs.append('shares victory')
        if len(fs) > 1:
            fs[-1] = 'and ' + fs[-1]
        return ', '.format(fs)

    def __str__(self):
        s = super(ChangeAllyOptions, self).__str__()
        a = self.f.player_name(self.ally_id)
        return '{0} {1} with {2}'.format(s, self.flagstr(), a)

class TransferResources(Action):

    id = 0x51
    size = 10
    apm = False

    def __init__(self, f, player_id, action_block):
        super(TransferResources, self).__init__(f, player_id, action_block)
        self.ally_id = b2i(action_block[1])
        offset = 2
        self.gold = b2i(action_block[offset:offset+DWORD])
        offset += DWORD
        self.lumber = b2i(action_block[offset:offset+DWORD])

    def __str__(self):
        s = super(TransferResources, self).__str__()
        a = self.f.player_name(self.ally_id)
        return '{0} transfered {1} gold and {2} lumber to {3}'.format(s, self.gold,
                                                                      self.lumber, a)

class MapTriggerChatCommand(Action):

    id = 0x60
    apm = False

    def __init__(self, f, player_id, action_block):
        super(MapTriggerChatCommand, self).__init__(f, player_id, action_block)
        offset = 1 + 2*DWORD
        s, i = nulltermstr(action_block[offset:])
        self.size = offset + i + 1

class EscapePressed(Action):

    id = 0x61
    size = 1
    apm = True

    def __init__(self, f, player_id, action_block):
        super(EscapePressed, self).__init__(f, player_id, action_block)

class ScenarioTrigger(Action):

    id = 0x62
    apm = False

    def __init__(self, f, player_id, action_block):
        super(ScenarioTrigger, self).__init__(f, player_id, action_block)
        self.size = 13 if self.f.build_num >= BUILD_1_07 else 9

class HeroSkillSubmenu(Action):

    le = BUILD_1_06
    id = (0x65, 0x66)
    size = 1
    apm = True

    def __init__(self, f, player_id, action_block):
        super(HeroSkillSubmenu, self).__init__(f, player_id, action_block)

class BuildingSubmenu(Action):

    le = BUILD_1_06
    id = (0x66, 0x67)
    size = 1
    apm = True

    def __init__(self, f, player_id, action_block):
        super(BuildingSubmenu, self).__init__(f, player_id, action_block)

class MinimapSignal(Action):

    le = BUILD_1_06
    id = (0x67, 0x68)
    size = 13
    apm = False

    def __init__(self, f, player_id, action_block):
        super(MinimapSignal, self).__init__(f, player_id, action_block)
        offset = 1
        x = b2f(action_block[offset:offset+DWORD])
        offset += DWORD
        y = b2f(action_block[offset:offset+DWORD])
        offset += DWORD
        self.loc = (x, y)

    def __str__(self):
        s = super(MinimapSignal, self).__str__()
        return '{0} at ({1:.3%}, {2:.3%})'.format(s, self.loc[0]/MAXPOS,
                                                     self.loc[1]/MAXPOS)

class ContinueGameB(Action):

    le = BUILD_1_06
    id = (0x68, 0x69)
    size = 17
    apm = False

    def __init__(self, f, player_id, action_block):
        super(ContinueGameB, self).__init__(f, player_id, action_block)

class ContinueGameA(Action):

    le = BUILD_1_06
    id = (0x69, 0x6A)
    size = 17
    apm = False

    def __init__(self, f, player_id, action_block):
        super(ContinueGameA, self).__init__(f, player_id, action_block)

class UnknownScenario(Action):

    id = 0x75
    size = 2
    apm = False

    def __init__(self, f, player_id, action_block):
        super(UnknownScenario, self).__init__(f, player_id, action_block)

# has to come after the action classes
_locs = locals()
ACTIONS = {a.id: a for a in _locs.values() if hasattr(a, 'id') and \
                                    isinstance(a.id, int) and a.id > 0}
ACTIONS_LE_1_06 = {a.id[0]: a for a in _locs.values() if hasattr(a, 'id') and \
                                    isinstance(a.id, tuple) and a.le == BUILD_1_06}
ACTIONS_GT_1_06 = {a.id[1]: a for a in _locs.values() if hasattr(a, 'id') and \
                                    isinstance(a.id, tuple) and a.le == BUILD_1_06}
ACTIONS_LE_1_14B = {a.id[0]: a for a in _locs.values() if hasattr(a, 'id') and \
                                    isinstance(a.id, tuple) and a.le == BUILD_1_14B}
ACTIONS_GT_1_14B = {a.id[1]: a for a in _locs.values() if hasattr(a, 'id') and \
                                    isinstance(a.id, tuple) and a.le == BUILD_1_14B}
del _locs

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
        if not self.closed:
            self.f.close()

    def __enter__(self):
        return self

    def __exit__(self ,type, value, traceback):
        if not self.closed:
            self.f.close()

    @property
    def loc(self):
        return self.f.tell()

    @loc.setter
    def loc(self, value):
        self.f.seek(value)

    @property
    def closed(self):
        return self.f.closed

    @property
    def mapname(self):
        return self.map_name

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
        
        if self.build_num < 6089:
            self.is_reforged = False
        else:
            self.is_reforged = True

    def _read_blocks(self):
        f = self.f
        self.loc = self.header_size
        data = b''
        for n in range(self.nblocks):
            block_size = b2i(f.read(WORD))
            if self.is_reforged == True:
                self.loc += 2
            block_size_decomp = b2i(f.read(WORD))
            
            self.loc += DWORD
            if self.is_reforged == True:
                self.loc += 2
                
            raw = f.read(block_size)
            # Have to use Decompression obj rather than the decompress() func.
            # This avoids 'incomplete or truncated stream' errors
            #   dat = zlib.decompress(raw, 15, block_size_decomp)
            d = zlib.decompressobj()
            dat = d.decompress(raw, block_size_decomp)
            if len(dat) != block_size_decomp:
                raise zlib.error("Decompressed data size does not match expected size.")
            data += dat
        self._parse_blocks(data)

    def _parse_blocks(self, data):
        self.events = []
        self.clock = 0
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
        self.map_checksum = str(binascii.hexlify(settings[9:]), 'utf-8')
        self.map_name, i = nulltermstr(decomp[13:])
        self.creator_name, _ = nulltermstr(decomp[13+i+1:])
        # back to less dense data
        self.player_count = b2i(data[offset:offset+4])
        offset += 4
        self.game_type = GAME_TYPES.get(b2i(data[offset]), 'unknown')
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
        if b2i(data[offset]) != 0x19:
            # read in reforged metadata player metadata
            offset += 12
            int_attempts = 0
            self.reforged_player_metadata = []
            while (b2i(data[offset]) != 0x19) & (int_attempts < 24):
                offset += 1
                self.reforged_player_metadata.append(ReforgedPlayerMetadata.from_raw(data[offset:]))
                offset += self.reforged_player_metadata[-1].size + 1
                int_attempts += 1
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
        self.select_mode = SELECT_MODES.get(b2i(data[offset]), 'unknown')
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
        elif self._lastleft is not None and (len(self.players) <=2):
            inc = True
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
        self.clock += dt
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
        actions = dict(ACTIONS)
        actions.update(ACTIONS_LE_1_06 if self.build_num <= BUILD_1_06 \
                       else ACTIONS_GT_1_06)
        actions.update(ACTIONS_LE_1_14B if self.build_num <= BUILD_1_14B \
                       else ACTIONS_GT_1_14B)
        while len(action_block) > 0:
            aid = b2i(action_block[0])
            action = actions.get(aid, None)
            if action is None:
                return
            e = action(self, player_id, action_block)
            self.events.append(e)
            action_block = action_block[e.size:]

    @lru_cache(13)
    def slot_record(self, pid):
        records = self.slot_records
        for sr in records:
            if sr.player_id == pid:
                break
        else:
            raise ValueError("could not find slot record for player ID {0}".format(pid))
        return sr

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
            p = self.slot_record(pid)
        return p

    @lru_cache(13)
    def player_name(self, pid):
        try:
            p = self.player(pid)
        except ValueError:
            return "unknown"
        if isinstance(p, SlotRecord):
            return 'observer'
        return p.name

    @lru_cache(13)
    def player_race(self, pid):
        p = self.player(pid)
        if p.race == 'none' and isinstance(p, Player):
            p = self.slot_record(pid)
        if p.race == 'none' or p.race == 'random':
            # guess race from the units used durring the first few seconds
            for e in self.events[:50]:
                if e.player_id != pid:
                    continue
                if hasattr(e, 'ability') and e.ability in ITEMS_TO_RACE:
                    return ITEMS_TO_RACE[e.ability]
        return p.race

    @lru_cache(13)
    def player_race_random(self, pid):
        p = self.player(pid)
        if p.race == 'none' and isinstance(p, Player):
            p = self.slot_record(pid)
        if p.race == 'random':
            return True
        return False

    def print_apm(self):
        acts = {p.id: 0 for p in self.players}
        for e in self.events:
            if e.apm:
                acts[e.player_id] += 1
        mins = self.clock / (60 * 1000.0)
        m = "Actions per minute over {0:.3} min".format(mins)
        print('-' * len(m))
        print(m)
        for pid, act in sorted(acts.items()):
            if act == 0:
                continue
            print("  {0}: {1:.5}".format(self.player_name(pid), act/mins))

    def timeseries_actions(self):
        """Returns timeseries of cummulative number of actions, as measured
        by actions per minute.
        """
        acts = {p.id: ([0], [0]) for p in self.players}
        for e in self.events:
            if not e.apm:
                continue
            t, a = acts[e.player_id]
            if e.time == t[-1]:
                a[-1] += 1
            else:
                t.append(e.time)
                a.append(a[-1] + 1)
        acts = {pid: (t, a) for pid, (t, a) in acts.items() if len(t) > 1}
        return acts

    def timegrid_actions(self, dt=1000, dur=120*60*1000):
        """Returns timeseries of cummulative number of actions, as measured
        by actions per minute, but on an evenly spaced grid of dt miliseconds
        of duration dur [miliseconds]. Defaults to 1 second time steps over 2 hrs.
        """
        nsteps = (dur//dt) + 1
        acts = {p.id: [0, 0] for p in self.players}
        for e in self.events:
            if not e.apm:
                continue
            a = acts[e.player_id]
            if e.time//dt == len(a) - 2:
                a[-1] += 1
            else:
                a.append(a[-1] + 1)
        acts = {pid: a + a[-1:]*(nsteps - len(a)) for pid, a in acts.items()
                                                  if len(a) > 2}
        return acts

    def winner(self):
        for e in self.events[-1:-300:-1]:
            if not isinstance(e, LeftGame):
                continue
            result = e.result()
            if result == 'won':
                return e.player_id
            elif result == 'lost':
                players = [sr.player_id for sr in self.slot_records \
                           if sr.team < 12 and sr.player_id > 0]
                if e.player_id not in players:
                    continue
                winner = [pid for pid in players if pid != e.player_id][0]
                return winner
        # if no one won or lost, find out who said gg and left
        players = {sr.player_id for sr in self.slot_records \
                   if sr.team < 12 and sr.player_id > 0}
        for e in self.events[-1:-300:-1]:
            if not isinstance(e, LeftGame):
                continue
            if e.player_id not in players:
                continue
            if e.result() != 'left':
                continue
            chats = {c.msg.lower() for c in self.events[-300:] \
                        if isinstance(c, Chat) and c.player_id == e.player_id}
            if 'g' in chats or 'gg' in chats:
                # is loser
                winner = [pid for pid in players if pid != e.player_id][0]
                return winner
        # if all else fails, find the last player to leave
        for e in self.events[-1:-300:-1]:
            if isinstance(e, LeftGame) and e.player_id in players:
                return e.player_id
        raise RuntimeError("Winner could not be found")

    @lru_cache(13)
    def map(self):

        if self.map:
            return self.map
        else:
            return "No map found"


def main():
    f = File(sys.argv[1])
    for event in f.events:
        print(event)
    f.print_apm()
    print('-' * 10)
    print('The winner is {0}'.format(f.player_name(f.winner())))
    #print(f.version_num)
    #print(f.build_num)

if __name__ == '__main__':
    main()
