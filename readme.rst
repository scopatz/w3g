W3G: The Warcraft 3 Replay File Format
--------------------------------------
This is a single module package that contains everything that is needed to 
read in the Warcraft 3 replay file format ``*.w3g``.  W3G is a custom 
binary format.  The benefits of this are that the files are small, even for 
very long games.  The downside is that for them to be meaningfully a lot of 
extra data needs to be provided (as is done here for you) for these files
to be meaningfully deciphered.

The replays basically amount to a bunch of metadata (map, players, etc) and a 
big event list.  The file parser here provides you with access to this data 
as well as some post-processed metrics, such as actions-per-minute (APM).  

The API should be easy to use and figure out. Classes and attributes are named in a
sane way. Here is an example of usage::

    import w3g
    f = w3g.File('replay.w3g')

    winner = f.winner()
    print(winner)

    f.print_apm()

You can also use this file in script mode to print out the entire game and 
its stats::

    $ ./w3g.py  replay.w3g

If you have any questions or issues, please email me or leave an issue on the 
issue tracker.

/scopzout