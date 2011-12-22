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

poker.py
    This script contains many core util methods for computing hand values, 
    printing, etc.
"""

import pickle,copy,logging,time,sys,shelve,traceback,bsddb,threading,doctest
import hotshot, hotshot.stats

log = logging.getLogger("poker.poker")
log.setLevel(logging.INFO)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

try:
    import psyco
except ImportError:
    log.info("Download the 'psyco' Python module for some instant speedups.")
    pass

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

from poker_globals import *

global pokervals6_db, pokervals7_db
pokervals6_db = None
pokervals7_db = None

def getpokerval(_cards,pokerval_db=None):
    """ Calculate the best hand possible from a list of cards via database lookup. 
    
    _cards should be a list 5 or more 2-tuples of the form (card value, suit id).  They 
    need not be sorted in any particular order.
    
    Returns a 32-bit integer "pokerval" which can be compared (as an int)
    to other pokervals to determine the comparative hand strength.  The pokerval
    can be understood in a bitwise manner:
    
        2^31 is true for a straight flush.
        2^30 is true for four of a kind.
        2^29 is true for a full house.
        2^28 is true for a flush.
        2^27 is true for a straight.
        2^26 is true for three of a kind.
        2^25 is true for two pair.
        2^24 is true for one pair.
        bits 20-23 are unused.
        2^19 to 2^16 represents the high value
            14d/Eh == High Ace
            13d/Dh == King
            ...
            2 == Deuce
            1 == Low Ace
        2^15 to 2^12 is the 2nd value
        2^11 to 2^8 is the 2nd value
        2^7 to 2^4 is the 2nd value
        2^3 to 2^0 is the low value
        
    An example of _cards might be Ac 2c 3c 4c 5c 8c 10d, which would look
    like this: [(14,1),(2,1),(3,1),(4,1),(5,1),(8,1),(10,2)]

    >>> getpokerval([(14,1),(2,1),(3,1),(4,1),(5,1),(8,1),(10,2)]) == STRAIGHTFLUSH + 0x54321
    True
    >>> getpokerval([(10,2),(8,1),(3,1),(4,1),(5,1),(6,1),(14,1)]) == FLUSH + 0xe8654
    True
    >>> format_pokerval(getpokerval([(10,2),(8,1),(3,1),(4,1),(5,1),(6,1),(14,1)]))
    '00010000 0xe8654 FLUSH'
    """
    if len(_cards)<5:
        return None
        
    global pokerval_cache,pokerval_cachehits,pokerval_cachemisses
    cards = _cards
    cards.sort()
    cards = normalize_suits(cards)
    cards.sort()

    try:
        index = make_stringindex(cards)
        if pokerval_db is not None and len(index)==7:
            return pokerval_db[index]
        else:
            try:
                pokerval = pokerval_cache[index]
                pokerval_cachehits+=1
                return pokerval
            except KeyError:
                pokerval_cachemisses+=1
                pass

            if pokervals6_db is None:
                open_dbs()
            if len(index)==5:
                pokerval = Hand(cards).getpokerval()
            elif len(index)==6:
                pokerval = pokervals6_db[index]
            elif len(index)==7:
                pokerval = pokervals7_db[index]
            else:
                raise ValueError("what did you call this with? : index=%s, len=%d"%(index,len(index)))

            #~ ### hack cause i fucked up low-Ace straights in the generated db
            #~ if (pokerval & STRAIGHT):
                #~ if (pokerval & 0xFFFFF) == 0x54321:
                    #~ if cards[4][0]==6:
                        #~ if cards[5][0]==7:
                            #~ pokerval = pokerval - (pokerval & 0xFFFFF) + 0x76543
                        #~ else:
                            #~ pokerval = pokerval - (pokerval & 0xFFFFF) + 0x65432
            #~ elif (pokerval & STRAIGHTFLUSH):
                #~ if (pokerval & 0xFFFFF) == 0x54321:
                    #~ if cards[4][0]==6 and cards[4][1]==1:
                        #~ if cards[5][0]==7 and cards[5][1]==1:
                            #~ pokerval = pokerval - (pokerval & 0xFFFFF) + 0x76543
                        #~ else:
                            #~ pokerval = pokerval - (pokerval & 0xFFFFF) + 0x65432

            pokerval_cache[index] = pokerval
    except KeyError:
        errstr = "hand not in database: %s %s, <%s>, %s"%(format_cards(_cards),format_cards(cards),index,reverse_stringindex(index))
        raise KeyError(errstr)
    except:
        raise
    log.debug("[pokerval] %s=%s"%(format_cards(cards),format_pokerval(pokerval)))
    return pokerval

def _make_char(card):
    """ Makes a single character from a card (value,suit) 2-tuple.
    Example use: index = "".join(map(_make_char,seven_cards))
    """
    #print "make_char: ",card,chr(((card[0])<<4)+(card[1]-1))
    if card[1]==0:
        raise ValueError
    return chr(((card[0])<<4)+(card[1]-1))

def make_stringindex(cards):
    return "".join([_make_char(c) for c in cards])
    
try:
    psyco.bind(_make_char)    
    psyco.bind(make_stringindex)
except:
    pass
    
def reverse_stringindex(index):
    """ Prettyprint a make_char-made index. """
    cards = []
    for c in index:
        i = ord(c)
        rank = (i & 0xf0)>>4
        suit = (i & 0x0f)+1
        #print c,i,rank,suit
        cards.append((rank,suit))
    return cards

class Pocket:
    """ A set of two cards.  May be compared to other pockets or strings like "KQo" or "AJ". """
    def __init__(self,c1,c2=None):
        if c2 is None:
            self.cards = c1
        else:
            self.cards = [c1,c2]
        self.cards.sort(reverse=True)
    def __eq__(self,other):
        if isinstance(other,Pocket):
            return self.cards == other.cards
        elif type(other) is str:
            if other[0] not in ('x','X') and cvt_to_rank(other[0]) != self.cards[0][0]:
                return False
            if other[1] not in ('x','X') and cvt_to_rank(other[1]) != self.cards[1][0]:
                return False
            if len(other)==3:
                if other[-1] in ("o","O"): # check suit for inequality
                    return self.cards[0][1] != self.cards[1][1]
                elif other[-1] in ("s","S"): # check suit for equality
                    return self.cards[0][1] == self.cards[1][1]
            else:
                return True
        else:
            return False
    def __ne__(self,other):
        return not self.__eq__(other)
    def __str__(self):
        return "cards: %s"%(str(self.cards))


class PokervalCalculator:
    """ A set of five cards that calculates a pokerval. """
    def __init__(self,cards,pokerval_to_beat=0):
        self.sethand(cards,pokerval_to_beat)
    def __str__(self):
        pokerval = self.getpokerval()
        s=format_cards(self.cards) + ' val: '
        return s+format_pokerval(pokerval)
    def sethand(self,h_in,pokerval_to_beat=0):
        self.precalculated_isstraight = None
        self.precalculated_isflush = None

        self.valuecount = {}

        self.cards = []
        if len(h_in) != 5:
            raise "Hand can be made only of exactly 5 cards, not %d!"%len(h_in),h_in
        for card in h_in:
            if type(card) is list or type(card) is tuple:
                if len(card)!=2:
                    raise "wrong number of values in card (should be 2)",card
                self.cards.append((card[0], card[1]))
            else:
                raise "illegal card being inserted into hand!",card,h_in
        self.cards.sort()

        for card in self.cards:
            try: # keep bins for pair analysis later
                self.valuecount[card[0]] += 1
            except:
                self.valuecount[card[0]] = 1

        self.pokerval = None
        self.getpokerval(pokerval_to_beat)

    def isflush(self):
        if self.precalculated_isflush is None:
            self.precalculated_isflush = True
            lastsuit = self.cards[0][1]
            for card in self.cards:
                if lastsuit != card[1]:
                    self.precalculated_isflush = False
                    break

        return self.precalculated_isflush

    def isstraight(self):
        if self.precalculated_isstraight is None:
            if self.cards[0][0]==self.cards[1][0]-1==self.cards[2][0]-2==self.cards[3][0]-3:
                if self.cards[4][0]-4==self.cards[0][0] or (self.cards[4][0]==14 and self.cards[0][0]==2):
                    self.precalculated_isstraight = True
                else:
                    self.precalculated_isstraight = False
            else:
                self.precalculated_isstraight = False

        return self.precalculated_isstraight

    def getpairings(self):
        #ranksets = self.valuecount.values()
        most=0
        mostrank = 0
        secondrank = 0
        secondmost = 0
        for (rank,count) in self.valuecount.iteritems():
            if count > most:
                secondmost,most = most,count
                secondrank,mostrank = mostrank,rank
            elif count > secondmost:
                secondmost = count
                secondrank = rank
        return (most,mostrank,secondmost,secondrank)

    def getpokerval(self, pokerval_to_beat=0):
        """ If pokerval_to_beat is larger than this one can ever be,
        then give up... no longer interested. """

        if self.pokerval is not None:
            return self.pokerval

        self.pokerval = 0

        #print "start getpokerval",
        (most,mostrank,secondmost,secondrank)=self.getpairings()
        #print (most,mostrank,secondmost,secondrank),
        if most==4:
            self.pokerval |= (most==4) * FOUROFAKIND # four of a kind
            self.pokerval |= (mostrank << 16) | (mostrank <<12) | (mostrank<<8) | (mostrank<<4)  | secondrank
        elif most==3:
            if secondmost==2:
                self.pokerval |= FULLHOUSE # fullhouse
                self.pokerval |= (mostrank << 16) | (mostrank <<12) | (mostrank<<8) | (secondrank<<4)  | secondrank
            else:
                self.pokerval |= THREEOFAKIND # three of a kind
                if self.cards[4][0] != mostrank:
                    fourthrank = self.cards[4][0]
                    if self.cards[3][0] != mostrank:
                        fifthrank = self.cards[3][0] # 5 4 3 3 3
                    else:
                        fifthrank = self.cards[0][0] # 5 4 4 4 3
                else:
                    fourthrank = self.cards[1][0]
                    fifthrank = self.cards[0][0] # 5 5 5 4 3

                self.pokerval |= (mostrank << 16) | (mostrank <<12) | (mostrank<<8) | (fourthrank<<4)  | fifthrank
        elif (self.isflush()) or (self.isstraight()):
            if self.isflush() and self.isstraight():
                self.pokerval |= STRAIGHTFLUSH # strflush
            elif self.isflush():
                self.pokerval |= self.isflush() * FLUSH # flush
            else:
                self.pokerval |= self.isstraight() * STRAIGHT # straight
            self.pokerval |= (self.cards[4][0]<<16) | ( self.cards[3][0]<<12) | (self.cards[2][0]<<8) | (self.cards[1][0]<<4)  | self.cards[0][0]
            if self.isstraight():
                if (self.pokerval & 0xFFFFF) == 0xe5432:
                    self.pokerval= self.pokerval - (self.pokerval& 0xFFFFF) + 0x54321

        elif most==2:
            if secondmost==2: # two pair
                self.pokerval |= 1*TWOPAIR # 2 pair
                if mostrank > secondrank:
                    hipairrank = mostrank
                    lopairrank = secondrank
                else:
                    hipairrank = secondrank
                    lopairrank = mostrank
                for c in self.cards:
                    if c[0] != hipairrank and c[0] != lopairrank:
                        fifthrank = c[0]
                        break
                self.pokerval |= (hipairrank << 16) | (hipairrank  <<12) | (lopairrank<<8) | (lopairrank<<4)  | fifthrank

            else: # one pair
                rest = []
                for c in self.cards:
                    if c[0]!=mostrank:
                        rest.append(c[0])
                self.pokerval |= 1 *ONEPAIR
                self.pokerval |= (mostrank << 16) | (mostrank  <<12) | (rest[2]<<8) | (rest[1]<<4)  | rest[0]

        else: # high card
            self.pokerval |= (self.cards[4][0]<<16) | ( self.cards[3][0]<<12) | (self.cards[2][0]<<8) | (self.cards[1][0]<<4)  | self.cards[0][0]

        #print self

        return self.pokerval

class PokervalReader:
    """ A set of five cards that fetches a pokerval from the precomputed file. """

    pokervals = None
    def readinpokervals(self):
        if Hand.pokervals is None:
            #raise
            #print "Loading pokervals.p..."
            #Hand.pokervals = pickle.load(open('5cardpokervals_orderedsuits.p','rb'))
            Hand.pokervals = shelve.open('pokervals.shelf','r')
            #print "Done loading pokervals!"

    def __init__(self,cards,junk=None):
        self.sethand(cards)

    def __str__(self):
        pokerval = self.getpokerval()
        s=format_cards(self.cards) + ' val: '
        return s+format_pokerval(pokerval)

    def sethand(self,h_in):
        self.cards = []
        if len(h_in) != 5:
            raise "Hand can be made only of exactly 5 cards, not %d!"%len(h_in),h_in
        for card in h_in:
            if type(card) is list or type(card) is tuple:
                if len(card)!=2:
                    raise "wrong number of values in card (should be 2)",card
                self.cards.append((card[0], card[1]))
            else:
                raise "illegal card being inserted into hand!",card,h_in

        self.readinpokervals()
        self.cards.sort()
        self.cards = normalize_suits(self.cards)
        self.cards.sort()
        try:
            #self.pokerval = Hand.pokervals[calchandint(self.cards)]
            index = make_stringindex(self.cards)
            #print reverse_stringindex(index)
            self.pokerval = Hand.pokervals[index]
            #print "found index: %s, %x"%(format_cards(self.cards),calchandint(self.cards))
        except KeyError:
            self.pokerval = 0
            raise ValueError("dammit, that hand is illegal/couldn't find that index: %s, %x"%(format_cards(self.cards),calchandint(self.cards)))
            #raise

    def getpokerval(self):
        return self.pokerval

#Hand = PokervalCalculator
Hand = PokervalReader

def getbesthand(cards):
    """ Return the best Hand possible from a list of cards. """
    if len(cards)<5:
        return None

    maxpokervalue = 0
    bestpokerhand = None
    for cardset in xuniqueCombinations(cards,5):
        #print enemy_pokerval, maxpokervalue
        hand = Hand(cardset,maxpokervalue)
        #print hand,
        curpokervalue = hand.getpokerval()
        #print curpokervalue
        if curpokervalue > maxpokervalue:
            maxpokervalue = curpokervalue
            bestpokerhand = hand

    return bestpokerhand

def open_dbs():
    global pokervals6_db, pokervals7_db
    pokervals6_db = shelve.BsdDbShelf(bsddb.hashopen('pokervals6.shelf','r'))
    pokervals7_db = shelve.BsdDbShelf(bsddb.hashopen('pokervals7.shelf','r'))

def close_dbs():
    global pokervals6_db, pokervals7_db
    if pokervals6_db is not None:
        pokervals6_db.close()
        pokervals6_db = None
    if pokervals7_db is not None:
        pokervals7_db.close()
        pokervals7_db = None
    

global pokerval_cache,pokerval_cachehits,pokerval_cachemisses,weightedcomparehands_cache,weightedcomparehands_cachehits

def clear_pokerval_cache():
    global pokerval_cache,pokerval_cachehits,pokerval_cachemisses,weightedcomparehands_cache,weightedcomparehands_cachehits
    pokerval_cache={}
    weightedcomparehands_cache={}
    pokerval_cachehits=0
    pokerval_cachemisses=0
    weightedcomparehands_cachehits=0
clear_pokerval_cache()

def isstraight(_cards):
    """ is a bunch of cards a straight? """
    pv = getpokerval(_cards)
    #print (format_pokerval(pv))
    return (STRAIGHT & pv)>0

def isbetterhand(cards,enemy_pokerval):
    """ Are my 5,6, or 7 cards better than enemy_pokerval? """

    for cardset in xuniqueCombinations(cards,5):
        #print enemy_pokerval, maxpokervalue
        hand = Hand(cardset,enemy_pokerval)
        #print hand,
        curpokervalue = hand.getpokerval()
        #print curpokervalue > enemy_pokerval, cardset, "%s v. %s"%(format_pokerval(curpokervalue) ,format_pokerval(enemy_pokerval) )
        if curpokervalue > enemy_pokerval:
            return True

    return False

def whowins(mycards,enemiescards,commoncards,potentialcommoncards=None):
    allmycards = copy.copy(mycards)
    allmycards.extend(commoncards)
    if potentialcommoncards is not None:
        allmycards.extend(potentialcommoncards)

    if len(allmycards)!=7:
        raise "calling whowins wrong!  len of commoncards+potentialcommoncards must be 7! common=%s potential=%s allmycards=%s"%(commoncards,potentialcommoncards,allmycards)

    mybest = getpokerval(allmycards)
    hisbest = 0
    for hiscards in enemiescards:
        allhiscards = copy.copy(hiscards)
        allhiscards.extend(commoncards)
        if potentialcommoncards is not None:
            allhiscards.extend(potentialcommoncards)
    
        #~ mybest = getbesthand(allmycards).getpokerval()
        #~ hisbest = getbesthand(allhiscards).getpokerval()
        hisbest = max(hisbest,getpokerval(allhiscards))
    if mybest > hisbest:
        winner = 1
        winnertxt = "WIN"
    elif mybest < hisbest:
        winner = 0
        winnertxt = "LOSE"
    else:
        winner = .5
        winnertxt = "TIE"

    log.debug("potentials: %s %s\n\tme  %s\n\thim %s"%(format_cards(potentialcommoncards), winnertxt, format_pokerval(mybest),format_pokerval(hisbest)))
    return winner

# counts the possible combination of hands that we win lose or tie against in a showdown right now
def nhands(mycards,commoncards):
    """ How many hands are higher than/lower than/tied with mine in a
    showdown right now given 3, 4, or 5 common cards? Return tuple:
    (nhandshi, nhandslo, nhandsti) """
    global log
    #log.debug("nhands: %s  common %s"%(format_cards(mycards),format_cards(commoncards)))

    nhandshi,nhandslo,nhandsti = 0,0,0
    total_cnt = 0

    allmycards = copy.copy(mycards)
    allmycards.extend(commoncards)

    if len(allmycards)<5 or len(allmycards)>7:
        raise "calling nhands wrong!  len of mycards+commoncards must be between 5 and 7 inclusive! common=%s allmycards=%s"%(commoncards,mycards)

    mybest = getpokerval(allmycards)
    # make deck excluding known cards
    deck = []
    for val in range(2,15):
        for suit in range(1,5):
            if (((val, suit) not in mycards) and
                ((val, suit) not in commoncards)):
                deck.append((val,suit))

    for potentialoppcards in xuniqueCombinations(deck,2):
        alloppcards = copy.copy(potentialoppcards)
        alloppcards.extend(commoncards)
        oppbest = getpokerval(alloppcards)
        if oppbest>mybest: nhandshi += 1
        elif oppbest<mybest: nhandslo += 1
        elif oppbest==mybest: nhandsti += 1
        else: raise "error in nhands! potentialoppcards=%s mycards=%s commoncards=%s"%(potentialoppcards,mycards,commoncards)

    return (nhandshi, nhandslo, nhandsti)

# calculates odds that we can win a showdown right now against a provided # of players if they have random hands
def prwinnow(nhandshi,nhandslo,nhandsti,nopponentsplaying=1):
    nhands = nhandshi+nhandslo+nhandsti
    if (nhands<=0):
        raise "Invalid call of prwinnow, nhands:%d"%(nhands)
    return pow(float(nhandslo)/nhands,nopponentsplaying)

def comparehands(mycards,enemiescards,commoncards,force_unweighted=False):
    """ Are my 2 cards better than his 2 (estimated) cards
    given 3, 4, or 5 common cards? Return the expected win %
    (money_made / total_wagered) """
    
    if len(commoncards)==3 and not force_unweighted:
        return weightedcomparehands(mycards,enemiescards,commoncards)

    if enemiescards is None or len(enemiescards)==0:
        return None

    if type(enemiescards[0][0]) is int:
        enemiescards = [enemiescards,]

    #~ log.info("comparehands: %s vs. %s common %s"%(format_cards(mycards),str([format_cards(hiscards) for hiscards in enemiescards]),format_cards(commoncards)))

    for e in enemiescards:
        for (i,c) in enumerate(e):
            e[i]=(c[0],c[1]) # make sure it's a tuple
            
    money = 0
    total_cnt = 0

    if len(commoncards)==5:
        return whowins(mycards,enemiescards,commoncards)
    elif len(commoncards)<5:
        # make deck
        deck = []
        for val in range(2,15):
            for suit in range(1,5):
                if (((val, suit) not in mycards) and
                    ((val, suit) not in commoncards)):
                    throwout=False
                    for hiscards in enemiescards:
                        if (val,suit) in hiscards:
                            throwout=True
                            break
                    if not throwout:
                        deck.append((val,suit))

        #print mycards,hiscards,commoncards
        for potentialcommoncards in xuniqueCombinations(deck,5-len(commoncards)):
            winner = whowins(mycards,enemiescards,commoncards,potentialcommoncards)
            #~ log.info("comparehands: %s v. %s common %s+%s result: %f"%(format_cards(mycards),
                #~ str([format_cards(hiscards) for hiscards in enemiescards]), 
                #~ format_cards(commoncards),
                #~ format_cards(potentialcommoncards),
                #~ winner))
            money += winner
            total_cnt += 1
        log.debug("comparehands: %s v. %s common %s result: %f"%(format_cards(mycards),
            str([format_cards(hiscards) for hiscards in enemiescards]), 
            format_cards(commoncards),
            float(money) / total_cnt))
        return float(money) / total_cnt
    else:
        raise "too many common cards!",commoncards

def weightedcomparehands_threadedattempt(mycards,enemiescards,commoncards,pokerval_db=None):
    """ Are my 2 cards better than his 2 (estimated) cards
    given 3, 4, or 5 common cards? Return the expected win %
    (money_made / total_wagered) """
    #log.info("comparehands: %s vs. %s common %s"%(format_cards(mycards),format_cards(enemiescards),format_cards(commoncards)))

    # check to see if it's a single enemy, then make it a list...
    if enemiescards is None or len(enemiescards)==0:
        return None

    global weightedcomparehands_cache,weightedcomparehands_cachehits

    weightedcomparehands_cache_index = pickle.dumps((mycards,enemiescards,commoncards),2)
    try:
        winpct = weightedcomparehands_cache[weightedcomparehands_cache_index]
        weightedcomparehands_cachehits+=1
        return winpct
    except KeyError:
        pass

    if type(enemiescards[0][0]) is int:
        enemiescards = [enemiescards,]

    for e in enemiescards:
        for (i,c) in enumerate(e):
            e[i]=(c[0],c[1]) # make sure it's a tuple

    #print "comparehands: %s vs. %s common %s"%(str(mycards),str(enemiescards),str(commoncards))

    # make deck
    deck = []
    for val in range(2,15):
        for suit in range(1,5):
            if (((val, suit) not in mycards) and
                ((val, suit) not in commoncards)):
                throwout=False
                for hiscards in enemiescards:
                    if (val,suit) in hiscards:
                        throwout=True
                        break
                if not throwout:
                    deck.append((val,suit))
    winsatturn = winsatriver = wins = 0.
    total_turn_cnt = total_cnt = 0.
    # umm..

    def calc_thread(result,mycards,enemiescards,commoncards,potentialfirstcard):
        result['winsatturn'] = 0.
        result['winsatriver'] = 0.
        result['total_cnt'] = 0.

        allmycards = copy.copy(mycards)
        allmycards.extend(commoncards)
        allmycards.append(potentialfirstcard)
        alltheircards = []

        for hiscards in enemiescards:
            allhiscards = copy.copy(hiscards)
            allhiscards.extend(commoncards)
            allhiscards.append(potentialfirstcard)
            alltheircards.append(allhiscards)

        #mybest6 = getbesthand(allmycards).getpokerval()

        mybest6 = getpokerval(allmycards)
        hisbest6 = 0.
        for allhiscards in alltheircards:
            #print format_cards(allhiscards), alltheircards
            #hisbest6 = max(hisbest6,getbesthand(allhiscards).getpokerval())
            hisbest6 = max(hisbest6,getpokerval(allhiscards))

        if mybest6 > hisbest6:
            winner6 = 1.
        elif mybest6 < hisbest6:
            winner6 = 0.
        else:
            winner6 = .5
        #print "potentials: %s %d\nme  %s\nhim %s"%(str((potentialfirstcard,None)), winner6, getbesthand(allmycards),getbesthand(allhiscards))
        result['winsatturn'] += winner6
        #~ total_turn_cnt += 1

        for (j,potentialsecondcard) in enumerate(deck[i+1:]):
            #print len(deck), len(deck[i+1:])

            allmycards = copy.copy(mycards)
            allmycards.extend(commoncards)
            allmycards.extend((potentialfirstcard,potentialsecondcard))
            alltheircards = []

            for hiscards in enemiescards:
                allhiscards = copy.copy(hiscards)
                allhiscards.extend(commoncards)
                allhiscards.extend((potentialfirstcard,potentialsecondcard))
                alltheircards.append(allhiscards)

            ###mybest = getbesthand(allmycards).getpokerval()
            mybest = getpokerval(allmycards,pokerval_db)
            hisbest = 0.
            for allhiscards in alltheircards:
                #print format_cards(allhiscards), alltheircards
                ###hisbest = max(hisbest,getbesthand(allhiscards).getpokerval())
                hisbest = max(hisbest,getpokerval(allhiscards,pokerval_db))

            if mybest > hisbest:
                winner = 1.
            elif mybest < hisbest:
                winner = 0.
            else:
                winner = .5

            #print "potentials: %s %d\nme  %s\nhim %s"%(str((potentialfirstcard,potentialsecondcard)), winner, getbesthand(allmycards),getbesthand(allhiscards))
            result['winsatriver'] += winner
            result['total_cnt'] += 1

    mythreads = []
    for (i,potentialfirstcard) in enumerate(deck):
        #print len(deck), len(deck[i+1:])
        result = {}
        athread = threading.Thread(target=calc_thread,args=(result,mycards,enemiescards,commoncards,potentialfirstcard))
        athread.start()
        mythreads.append([athread,result])
        #print "potentials: %s %d\nme  %s\nhim %s"%(str((potentialfirstcard,potentialsecondcard)), winner, getbesthand(allmycards),getbesthand(allhiscards))

    for (th,result) in mythreads:
        #print "waiting to join",
        th.join()
        #print "joined",total_turn_cnt
        winsatriver += result['winsatriver']
        winsatturn += result['winsatturn']
        total_cnt += result['total_cnt']
        total_turn_cnt += 1

    winpct = (float(winsatturn)/total_turn_cnt)*.75 + (float(winsatriver)/total_cnt*.25)

    #print "FINAL: ",total_cnt,"%.4f"%tempwinpct
    #print money,total_cnt
    #print "winpct: on turn %f, on river %f, blended %f"%(float(winsatturn)/total_turn_cnt,float(winsatriver)/total_cnt,winpct)
    weightedcomparehands_cache[weightedcomparehands_cache_index] = winpct
    return winpct

def weightedcomparehands(mycards,enemiescards,commoncards,pokerval_db=None,turn_weight=0.75):
    """ Are my 2 cards better than his 2 (estimated) cards
    given 3 common cards? Return the expected win %
    (money_made / total_wagered) """
    #log.info("comparehands: %s vs. %s common %s"%(format_cards(mycards),format_cards(enemiescards),format_cards(commoncards)))

    # check to see if it's a single enemy, then make it a list...
    if enemiescards is None or len(enemiescards)==0:
        return None

    global weightedcomparehands_cache,weightedcomparehands_cachehits

    if type(enemiescards[0][0]) is int:
        enemiescards = [enemiescards,]

    log.debug("[weightedcomparehands] %s vs. %s common %s"%(format_cards(mycards),str([format_cards(hiscards) for hiscards in enemiescards]),format_cards(commoncards)))

    weightedcomparehands_cache_index = pickle.dumps((mycards,enemiescards,commoncards),2)
    try:
        winpct = weightedcomparehands_cache[weightedcomparehands_cache_index]
        weightedcomparehands_cachehits+=1
        return winpct
    except KeyError:
        pass

    for e in enemiescards:
        for (i,c) in enumerate(e):
            e[i]=(c[0],c[1]) # make sure it's a tuple

    #print "comparehands: %s vs. %s common %s"%(str(mycards),str(enemiescards),str(commoncards))

    # make deck
    deck = []
    for val in range(2,15):
        for suit in range(1,5):
            if (((val, suit) not in mycards) and
                ((val, suit) not in commoncards)):
                throwout=False
                for hiscards in enemiescards:
                    if (val,suit) in hiscards:
                        throwout=True
                        break
                if not throwout:
                    deck.append((val,suit))
    winsatturn = winsatriver = wins = 0.
    total_turn_cnt = total_cnt = 0.
    # umm..


    for (i,potentialfirstcard) in enumerate(deck):

        if turn_weight>0.0:
            mybest6 = getpokerval(mycards + commoncards + [potentialfirstcard],pokerval_db)
            hisbest6 = max([getpokerval(hiscards + commoncards + [potentialfirstcard],pokerval_db) for hiscards in enemiescards])
    
            if mybest6 > hisbest6:
                winner6 = 1.
            elif mybest6 < hisbest6:
                winner6 = 0.
            else:
                winner6 = .5
            #print "potentials: %s %d\nme  %s\nhim %s"%(str((potentialfirstcard,None)), winner6, getbesthand(allmycards),getbesthand(allhiscards))
            winsatturn += winner6
        total_turn_cnt += 1

        for (j,potentialsecondcard) in enumerate(deck[i+1:]):
            #print len(deck), len(deck[i+1:])

            ###mybest = getbesthand(allmycards).getpokerval()
            mybest = getpokerval(mycards + commoncards + [potentialfirstcard,potentialsecondcard],pokerval_db)
            theirbest = max([getpokerval(hiscards + commoncards + [potentialfirstcard,potentialsecondcard],pokerval_db) for hiscards in enemiescards])

            if mybest > theirbest:
                winner = 1.
            elif mybest < theirbest:
                winner = 0.
            else:
                winner = .5

            #print "potentials: %s %d\nme  %s\nhim %s"%(str((potentialfirstcard,potentialsecondcard)), winner, getbesthand(allmycards),getbesthand(allhiscards))

            #money += winner*.25 + winner6*.75
            winsatriver += winner
            total_cnt += 1
            #tempwinpct = (float(winsatturn)/total_turn_cnt)*.75 + (float(winsatriver)/total_cnt*.25)
            #if (int(total_cnt) % 100)==0:
            #    print total_cnt,"%.4f"%tempwinpct

    #print "FINAL: ",total_cnt,"%.4f"%tempwinpct
    #print money,total_cnt
    winpct = (float(winsatturn)/total_turn_cnt)*turn_weight + (float(winsatriver)/total_cnt*(1.0-turn_weight))
    #print "winpct: on turn %f, on river %f, blended %f"%(float(winsatturn)/total_turn_cnt,float(winsatriver)/total_cnt,winpct)
    weightedcomparehands_cache[weightedcomparehands_cache_index] = winpct
    return winpct

def prbeat(enemy_pokerval, hand):
    """ Calculate the odds that, given your current 'hand', you'll beat
    a given pokerval.

    'hand' is a list of 2-tuples (rank,suit)

    """
    print "poker.prbeat: me: %s vs. %s"%(str(hand),format_pokerval(enemy_pokerval))
    if len(hand)<5:
        print """I can do this, but I don't think you want me to.
It'll take forever.  If you do, though, just remove this
return below.  There's 18424 possibilities just for 4 cards..."""
        return None

    # make deck
    deck = []
    for val in range(14,1,-1):
        for suit in range(1,5):
            if (val, suit) not in hand:
                deck.append((val,suit))

    winner_cnt = 0
    total_cnt = 0
    for extra_cards in xuniqueCombinations(deck,7-len(hand)):
        possiblecards = copy.copy(hand)
        possiblecards.extend(extra_cards)
        #print hand,extra_cards,possiblecards
        #print enemy_pokerval, possiblehand.getbesthand().pokerval
        if isbetterhand(possiblecards,enemy_pokerval):
            winner_cnt += 1
            print "better hand"
        else:
            print "worse hand"
        #print extra_cards,possiblehand.cards,possiblehand.getbesthand()
        total_cnt += 1
    print winner_cnt,total_cnt

    return float(winner_cnt) / float(total_cnt)

def normalize_suits(cards):
    """ Take a sequence of cards and change their suits so that the first suit encountered is always 0,
    and the next suit is 1, etc... an optimization to shrink the size of the possible hands...
    """
    #st = time.clock()
    if len(cards)==7:
        # check for flushability, if none, set suits to ccchhhh otherwise set flush suit to c and others to h

        suitcount = [0,0,0,0]
        for (rank,suit) in cards:
            suitcount[suit-1]+=1
        flushable_suit = None
        for (suitminus1,cnt) in enumerate(suitcount):
            if cnt>=5:
                flushable_suit = suitminus1+1
                break
        newcards = []
        #print "7cardbefore",flushable_suit, cards, suitcount
        if flushable_suit is None:
            i=0
            for (rank,suit) in cards:
                newcards.append((rank,(i%4)+1))
                i+=1
            #print "a",newcards
            return newcards
        else:
            lastsuitused=0
            flushnewsuit = None
            for (rank,suit) in cards:
                if suit == flushable_suit:
                    if flushnewsuit is None:
                        lastsuitused+=1
                        flushnewsuit = lastsuitused
                    newsuit = flushnewsuit
                else:
                    lastsuitused+=1
                    newsuit = lastsuitused
                newcards.append((rank,newsuit)) # should i plus1 to the newsuit? this is illegal 0-3 range but ...
            #print "b",newcards
            return newcards

    else:
        newsuit = {}
        lastsuitused=0
        for (rank,suit) in cards:
            if not newsuit.has_key(suit):
                lastsuitused+=1
                newsuit[suit] = lastsuitused
        #print "before",cards,newsuit
        newcards = []
        for card in cards:
            newcards.append((card[0],newsuit[card[1]]))
        #print "after",newcards

        return newcards

def calchandint(five_cards):
    handint = 0
    #print five_cards
    newfive = normalize_suits(five_cards)
    #newfive = five_cards
    #print five_cards,newfive
    for c in newfive:
        n = (c[0] << 2) | (c[1]-1)
        handint = (handint<<6) | n
    return handint

def enumall5cardhands():
    deck = []
    for val in range(2,15):
        for suit in range(1,5):
            deck.append((val,suit))
    cnt=0
    ### this method writes the file by hand
    f = open("5cardpokervals_handint.dat",'wb')
    allhands = {}
    for five_cards in xuniqueCombinations(deck,5):
        cnt = cnt+1
        handint = calchandint(five_cards)
        if not allhands.has_key(handint):
            hand = PokervalCalculator(five_cards)
            pokerval = hand.getpokerval()

            allhands[handint] = pokerval

            f.write(str(handint))
            f.write(' ')
            f.write(str(pokerval))
            f.write('\n')

        if cnt % 10000 == 1:
            print "ha",cnt, hand
            f.flush()

    f.close()

    ### this method pickles it to binary
    f = open('5cardpokervals_handint.p2','wb')
    pickle.dump(allhands,f,2)
    f.close()
    #~ f = open('5cardpokervals_handint.p','w')
    #~ pickle.dump(allhands,f,0)
    #~ f.close()

    print cnt

try:
    psyco.bind(normalize_suits)
    psyco.bind(getpokerval)
    psyco.bind(weighted_comparehands)
except:
    pass

def unittest_speed():
    print "1"
    print weightedcomparehands([(13, 3), (10, 3)], [[10, 2], [14, 1]] ,[(2, 2), (6, 3), (10, 1)])
    start_time = time.clock()
    print "2"
    print weightedcomparehands([(13, 3), (10, 3)], [[10, 2], [14, 1]] ,[(2, 2), (6, 3), (10, 1)])
    print "4"
    print weightedcomparehands([(12,1),(13,3)],[(9,1),(10,3)],[(3,2),(9,3),(12,2)])
    print "5"
    print weightedcomparehands([(12,1),(13,3)],[(3,1),(5,2)],[(3,2),(9,3),(12,2)])
    print "took %f seconds"%(time.clock()-start_time)
                
def unittest_calchandint():
    print calchandint([(5,2),(6,2),(7,2),(5,3),(2,2)])

def unittest_isstraight():
    print isstraight([(5,2),(6,2),(7,2),(5,3),(2,2),(8,2)])
    print isstraight([(5,2),(6,2),(7,2),(4,3),(2,2),(8,0)])
    print isstraight([(14,2),(2,2),(3,2),(5,3),(4,2),(8,0),(10,0)])
    print isstraight([(5,2),(6,2),(7,2),(5,3),(2,2),(8,0)])

def unittest_nhands():
    commoncards = cvt_to_cards(["Kd","7s","2c"])
    print "Commoncards:",format_cards(commoncards)
    nh = nhands(cvt_to_cards(["As","Kc"]),commoncards)
    print "AK:",nh,prwinnow(nh[0],nh[1],nh[2])
    nh = nhands(cvt_to_cards(["Kc","Qd"]),commoncards)
    print "KQ:",nh,prwinnow(nh[0],nh[1],nh[2])
    nh = nhands(cvt_to_cards(["Kc","4h"]),commoncards)
    print "K4:",nh,prwinnow(nh[0],nh[1],nh[2])
    nh = nhands(cvt_to_cards(["7c","Ah"]),commoncards)
    print "A7:",nh,prwinnow(nh[0],nh[1],nh[2])
    commoncards = cvt_to_cards(["9d","7s","2c"])
    print "Commoncards:",format_cards(commoncards)
    nh = nhands(cvt_to_cards(["As","9c"]),commoncards)
    print "A9:",nh,prwinnow(nh[0],nh[1],nh[2])
    nh = nhands(cvt_to_cards(["Td","9c"]),commoncards)
    print "T9:",nh,prwinnow(nh[0],nh[1],nh[2])
    nh = nhands(cvt_to_cards(["3d","9c"]),commoncards)
    print "93:",nh,prwinnow(nh[0],nh[1],nh[2])
    nh = nhands(cvt_to_cards(["Ac","7h"]),commoncards)
    print "A7:",nh,prwinnow(nh[0],nh[1],nh[2])

import unittest
class Test_getpokerval(unittest.TestCase):
    
    def setUp(self):
        clear_pokerval_cache()

    def test_getpokerval_lowAces(self):
        self.assertEqual(getpokerval([(14,1),(2,1),(3,1),(4,1),(5,1),(8,1),(10,1)]),STRAIGHTFLUSH + 0x54321)
        self.assertEqual(getpokerval([(14,1),(2,1),(3,1),(4,1),(5,1),(6,1),(10,1)]),STRAIGHTFLUSH + 0x65432)
        self.assertEqual(getpokerval([(14,1),(2,1),(3,1),(4,1),(5,1),(6,1),(7,1)]),STRAIGHTFLUSH + 0x76543)
        self.assertEqual(getpokerval([(14,2),(2,1),(3,1),(4,1),(5,1),(6,1),(7,1)]),STRAIGHTFLUSH + 0x76543)
        self.assertEqual(getpokerval([(14,1),(2,1),(3,2),(4,1),(5,1),(6,1),(7,1)]),FLUSH + 0xe7654)
        self.assertEqual(getpokerval([(14,1),(2,1),(3,1),(4,1),(5,1),(6,2),(7,1)]),STRAIGHTFLUSH + 0x54321)
        self.assertEqual(getpokerval([(14,1),(2,2),(3,1),(4,1),(5,1),(6,1),(7,1)]),STRAIGHTFLUSH + 0x76543)
        self.assertEqual(getpokerval([(14,1),(2,1),(3,2),(4,1),(5,2),(6,3),(7,1)]),STRAIGHT + 0x76543)
        self.assertEqual(getpokerval([(14,1),(2,2),(3,3),(4,4),(5,1),(6,2),(7,1)]),STRAIGHT + 0x76543)
        self.assertEqual(getpokerval([(14,1),(2,2),(3,3),(4,4),(5,1),(6,2),(8,1)]),STRAIGHT + 0x65432)
        self.assertEqual(getpokerval([(14,1),(2,2),(3,3),(4,4),(5,1),(8,2),(7,1)]),STRAIGHT + 0x54321)
        self.assertEqual(getpokerval([(14,1),(2,2),(3,3),(5,4),(5,1),(6,2),(7,1)]),ONEPAIR + 0x55e76)

class Test_pokerModule(unittest.TestCase):
    def setUp(self):
        clear_pokerval_cache()
        
    def assert_isClose(self,val,expected,thresh=0.00001):
        if abs(val-expected) < thresh:
            return True
        else:
            return False

    def test_comparetwohands(self):
        self.assert_isClose(0,comparehands([(14,1), (3,1)],[(3,3), (6,1)],[(5,2), (4,2), (2,3), (14,4), (13,4)]) )
    
        self.assert_isClose(0.0931818181818,weightedcomparehands([(13, 3), (10, 3)], [[10, 2], [14, 1]] ,[(4, 2), (6, 3), (10, 1)]) )
        self.assert_isClose(0.906439393939,weightedcomparehands([(10, 3), (8, 3)], 
                [
                    [[10, 2], [2, 1]]  # high pair
                   ] ,
                [(4, 2), (6, 3), (10, 1)]
                ))
        self.assert_isClose(0.806818181818,weightedcomparehands([(10, 3), (8, 3)], 
                [
                    [[5, 1], [7, 1]],  # straight draw
                   ] ,
                [(4, 2), (6, 3), (10, 1)]
                ))
        #60
        self.assert_isClose(0.709163898117,weightedcomparehands([(10, 3), (8, 3)], 
                [
                    [[5, 1], [7, 1]],  # straight draw
                    [[10, 2], [2, 1]]  # high pair
                   ] ,
                [(4, 2), (6, 3), (10, 1)]
                ))

    def test_pocket(self):
        p1 = Pocket((5,1),(7,2))
        p2 = Pocket((7,2),(5,1))
        p3 = Pocket((13,1),(12,1))
    
        self.assertEqual(p1,p2)
        self.assert_(not p1!=p2)
        self.assertNotEqual(p1,p3)
        ### convert the rest of these....
        if not(p1!=p3): print "fail4!"
        if p1=="KQo": print "fail5!"
        if "KQo"==p1: print "fail5.1!"
        if p1!="75": print "fail6!"
        if "75o"!=p1: print "fail6.1!"
        if p1!="75o": print "fail6.2"
        if p1=="75s": print "fail6.3"
        if p3 == "KQo": print "fail7"
        if p3 != "KQs": print "fail8"
        if p3 != "KQ": print "fail9"
    
        if p1 in ("KQo","KQs","71"): print "fail10"
        if p1 not in ("KQo","KQs","75"): print "fail11"
        if p3 in (p1,p2,"AK","KQo"): print "fail12"
        if p3 not in (p1,"KQs","AK"): print "fail12"
    
        if p1 == "xxs": print "fail13"
        if p1 != "xxo": print "fail14"
        if p1 != "xx": print "fail15"
        if p3 == "Kxo": print "fail16"
        if p1 == "Kx": print "fail17"
        if p3 != "Kx": print "fail18"
    
        print "tests complete"
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()    
    
if __name__ == '__main__':
    unittest.main()
   
    unittest_comparetwohands()
    import timeit
    profile=False
    if profile:
        profilefilename = 'poker_unittest.prof'
        prof = hotshot.Profile(profilefilename)
        print "profiling"
        prof.start()

    t = timeit.Timer("unittest_nhands()", "from __main__ import unittest_nhands")
    iters = 10
    print "test: %.2f msec/pass" % (1000 * t.timeit(number=1)/8)

    if profile:
        prof.close()
        stats = hotshot.stats.load(profilefilename)
        stats.sort_stats('time', 'calls')
        stats.print_stats(30)
