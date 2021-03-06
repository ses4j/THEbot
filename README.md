THEbot
======

A Texas Hold'em poker software library.

_Copyright (C) 2011 Scott Stafford_

Currently, the only code in this module is the bootstrapping code necessary to build a database
of hands that maps to their "pokerval", which is a 32-bit number that can be compared to other
pokervals to see which hand is better.  This library is therefore useful to do rapid comparisons of many 
hands.

Dependencies
------------
* Python 2.x (tested with 2.6 and 2.7)
* probstat for Python: http://sourceforge.net/projects/probstat/ (The Windows .pyd 
  file is included in this repository for convenience.)
* (optional) psyco: Latest Binaries available at http://www.voidspace.org.uk/python/modules.shtml.

Getting Started
---------------
For maximum performance, install Python 2.6 and the psyco module.  It will work fine
without, but it will run faster with it.

To play with the library, first run 'database_generator.py'
without arguments.  It will run for a while, generating
databases used to compute and compare poker hands.

