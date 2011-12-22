""" 
THEbot, a Texas Hold'em poker software library.
    Copyright (C) 2011  Scott Stafford

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

database_generator.py
    Execute this script to regenerate the precomputed databases of poker
    hands and their respective values: pokervals?.shelf for 5, 6, and 7 hands.
"""

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)

import poker,pickle,sys,shelve,anydbm,time
from poker_globals import *

global pokerval_cache,pokerval_cachehits,pokerval_cachemisses,weightedcomparehands_cache,weightedcomparehands_cachehits

try:
	import probstat
	xuniqueCombinations = probstat.Combination
except:
    def xuniqueCombinations(items, n): 
        if n==0:
            yield []
        else:
            for i in xrange(len(items)-n+1):
                for cc in xuniqueCombinations(items[i+1:],n-1):
                    yield [items[i]]+cc

def make_char(card):
    """ Makes a length-1 string from a card.
    example use: index = "".join(map(make_char,seven_cards))
    """
    return chr((card[0]<<4)+card[1])

def clear_pokerval_cache():
    global pokerval_cache,pokerval_cachehits,pokerval_cachemisses,weightedcomparehands_cache,weightedcomparehands_cachehits
    pokerval_cache={}
    weightedcomparehands_cache={}
    pokerval_cachehits=0
    pokerval_cachemisses=0
    weightedcomparehands_cachehits=0
clear_pokerval_cache()

def calculate_pokerval(_cards):
    global pokerval_cache,pokerval_cachehits,pokerval_cachemisses
    cards = poker.normalize_cards(_cards)
    try:
        index = poker.make_stringindex(cards)
        try:
            pokerval = pokerval_cache[index]
            pokerval_cachehits+=1
            return index, pokerval
        except KeyError:
            pokerval_cachemisses+=1
            pass

        pokerval = 0
        if len(cards) == 5:
            pokerval = poker.PokervalCalculator(cards).getpokerval()
        elif len(cards) > 5:
            for fivecards in xuniqueCombinations(cards,5):
                hand = poker.PokervalReader(fivecards)
                pokerval = max(pokerval, hand.getpokerval())
        else:
            raise ValueError("Not enough cards!")
            
        pokerval_cache[index] = pokerval
    except KeyError:
        errstr = "Hand not in database: %s %s, <%s>, %s"%(format_cards(_cards),format_cards(cards),index,reverse_stringindex(index))
        raise KeyError(errstr)
    except:
        raise

    return index,pokerval

def regenerate_database():
    """ go thru each possible hand and make a new db with the data items. """
    deck = []
    for val in range(2,15):
        for suit in range(1,5):
            deck.append((val,suit))
    
    possiblehands = {
        5: (2598960, 160537),
        6: (20358520, 1250964),
        7: (133784560,  210080),
    }
    
    allCombinations = sum([y[0] for (x,y) in possiblehands.iteritems()])
    
    print """
    
About to generate all 5, 6, and 7 card hands.  It takes a while
(there are %d possible combinations) so find something else to do for a bit.
If you kill the process at any time, no problem, you can resume it where it left off 
just by rerunning this method.
    
Let's begin...
    """ % allCombinations
    
    start_time_all = time.clock()
    for numcards in range(5, 8):
        i = 0
        
        clear_pokerval_cache()
        start_time = time.clock()
        db = shelve.open("pokervals"+str(numcards)+".shelf",protocol=2)
        try:
            num_computed = db["num_computed"]
        except KeyError:
            num_computed = 0
        (total, uniqueindices) = possiblehands[numcards]
        
        if len(db) != uniqueindices + 1: # +1 cause we store the counter in the database too, for restarting.
            print "Generating all "+str(total)+" possible "+str(numcards)+" card hands... "
            for cards in xuniqueCombinations(deck, numcards):
                i=i+1
                
                # enable skipping ahead if we ran halfway and terminated this process.
                if i<num_computed:  
                    continue
                    
                (idx,pokerval) = calculate_pokerval(cards)
                db[idx] = pokerval
                if i%100000 == 0:
                    now = time.clock()
                    print "%d%% of %d-card hands complete.  %d processed, %d unique, %.2fm elapsed (%.2fm total)." % (i*100.0/total, numcards, i, len(db), (now - start_time)/60.0, (now - start_time_all)/60.0)
                    
                    s = format_cards(cards) + ' val: '
                    print "\tLast Hand: ", s + format_pokerval(pokerval)
                    
                    db["num_computed"] = i
            print len(db)
        
        print "Your %d-card database is complete!  It has %d complete hands." % (numcards, len(db))
        
if __name__ == '__main__':
    regenerate_database()