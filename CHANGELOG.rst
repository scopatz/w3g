==============
w3g Change Log
==============

.. current developments

v1.0.3
====================

**Added:**

* Added ReforgedPlayerMetadata class.  This will hold the clan names for the various players once Blizzard full implements that feature.

**Fixed:**

* Can now also read replays from Warcraft 3 Reforged.



v1.0.2
====================

**Added:**

* Add support for 12 new slot colors
* Add new result to LeftGame. Not sure what it is, but it seems to be
  another version of 'left game'
* Add default value for Select Modes
* ``File.player_race()``: Try to guess actual race for Random players
* Add another "win condition" by finding the last Player who left the
  game

**Changed:**

* ``SlotRecord.from_raw()``: Drop 2 high-order bits in the "race" byte as
  per ``w3g_format.txt`` - 4.12 notes

**Fixed:**

* Prevent sporadic "invalid continuation byte" error
* Fix issue in ``Player.from_raw()`` which threw off byte seeking for the
  rest of the file

  - Usually custom_or_ladder should be 1 or 8, but it seems to often be
    2 for newer replays



v1.0.1
====================

**Fixed:**

* Some improvements to setup.py




v1.0.0
====================

**Fixed:**

* Minor fix for v1.29 file format




