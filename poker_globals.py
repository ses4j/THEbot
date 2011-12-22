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

poker_globals.py
    This script contains some constants and a few basic util methods.
    It's intended to be imported into the global namespace of the module.
"""

# actions
CALL = 1
RAIS = 2
FOLD = 3
CHECK = 4
BET = 5
ALLIN = 6
DONTKNOW = -1  # indeterminate/null/unset
WAIT = -2      # DO NOT ACT THIS CYCLE! i'm not ready...
TIMEDOUT = 7

PREFLOP = 1
FLOP = 2
TURN = 3
RIVER = 4

#base types
STRAIGHTFLUSH = 2**31
FOUROFAKIND = 2**30
FULLHOUSE = 2**29
FLUSH = 2**28
STRAIGHT = 2**27
THREEOFAKIND = 2**26
TWOPAIR = 2**25
ONEPAIR = 2**24

#more specific hand descriptions
i=12

HI = 1<<i; i=i+1
MID = 1<<i; i=i+1
LO = 1<<i; i=i+1
STORED = 1<<i; i=i+1
SUPERHISTRAIGHT = 1<<i; i=i+1
OVERPAIR = 1<<i; i=i+1
CRAP = 1<<i; i=i+1
FLUSHDRAW = 1<<i; i=i+1
CARDS = 1<<i; i=i+1
STRAIGHTDRAW = 1<<i; i=i+1
STICKKICKER = 1<<i; i=i+1
SUPERHI = 1 <<i;i=i+1


SECONDVALUE = 0xF00 #in bits 11-8, store the paired-with value for onepair
FIRSTVALUE = 0xF0 #in bits 4-7, store the paired-with value for onepair
TOPKICKER = 0xF

HIPAIR = ONEPAIR | HI
MIDPAIR = ONEPAIR | MID
LOPAIR = ONEPAIR | LO
HISTRAIGHT = STRAIGHT | HI
LOSTRAIGHT = STRAIGHT | LO
HITHREEOFAKIND = THREEOFAKIND | HI
MIDTHREEOFAKIND = THREEOFAKIND | MID
LOTHREEOFAKIND = THREEOFAKIND | LO
SUPERHIFULLHOUSE = FULLHOUSE | SUPERHI
TOPFULLHOUSE = FULLHOUSE | HI
HIFULLHOUSE = FULLHOUSE | HI
LOFULLHOUSE = FULLHOUSE | LO
TOPTWOPAIR = TWOPAIR | HI
HITWOPAIR = TWOPAIR | HI
MIDTWOPAIR = TWOPAIR | MID
LOTWOPAIR = TWOPAIR | LO
OVERCARDS = CARDS | HI

def format_action(action):
    if action==CALL:
        return 'CALL'
    elif action==CHECK:
        return 'CHECK'
    elif action==BET:
        return 'BET'
    elif action==RAIS:
        return 'RAIS'
    elif action==FOLD:
        return 'FOLD'
    elif action==ALLIN:
        return 'ALLIN'
    elif action==DONTKNOW:
        return 'n/a'
    elif action==WAIT:
        return 'WAIT'
    elif action==TIMEDOUT:
        return 'TIMEDOUT'
    else:
        raise "Tried to print illegal action! %s"%action

def format_actionlist_item(action):
    return "#%d %s %s on <%s>" \
        %(action['chair'],
            str(action['player']['name']),
            format_action(action['action']),
            str(action['assumed_hands']))

def format_actions(actions):
    if len(actions)==0:
        return "None."
    s = []

    for actionitem in actions:
        s.append(format_actionlist_item(actionitem))

    return "\n".join(s)

def rotate_to_start_with(start_chair, chairs):
    """ This function is like sorted() but will rotate the list of chairs
    around to start with the index in start_chair (or the next one after
    that if start_chair is not in the list.) """
    chairs_playing_redux = chairs+chairs+chairs

    #print "!!!!!",chairs_playing_redux
    for i in [x%10 for x in range(start_chair,start_chair+10)]:
        #print "!!!!! chair",i,
        try:
            startidx = chairs_playing_redux.index((i)%10)
            #print "found",dealeridx
            break
        except ValueError:
            #print "failed"
            continue
    if startidx is None:
        #log.exception("FIX - dunno what happened here but dealeridx is none: start_chair=%d, chairs=%s"%(start_chair,str(chairs)))
        #failed. no logging available.
        return chairs
    return chairs_playing_redux[startidx:len(chairs)+startidx]

def unittest_rotate_to_start_with():
    rotated = rotate_to_start_with(start_chair=3, chairs=range(10))
    print rotated
    assert(rotated==[3,4,5,6,7,8,9,0,1,2])

    rotated = rotate_to_start_with(start_chair=3, chairs=[7,8,1,4,6])
    print rotated
    assert(rotated==[4,6,7,8,1])

def format_handtype(handtype):
    s=''
    if handtype is None:
        return "None"
    if type(handtype) is str:
        s+=' preset_to=%s'%handtype
    elif type(handtype) is list or type(handtype) is tuple:
        s+=' preset_to=%s %s'%(format_cards(handtype),handtype)
    else:
        if HI & handtype: s+=' HI'
        if MID & handtype: s+=' MID'
        if LO & handtype: s+=' LO'
        if SUPERHI & handtype: s+=' SUPERHI'
        if STRAIGHTFLUSH & handtype: s+=' STRAIGHTFLUSH'
        if FOUROFAKIND & handtype: s+=' FOUROFAKIND'
        if FULLHOUSE & handtype: s+=' FULLHOUSE'
        if FLUSH & handtype: s+=' FLUSH'
        if STRAIGHT & handtype: s+=' STRAIGHT'
        if SUPERHISTRAIGHT & handtype: s+=' SUPERHISTRAIGHT'
        if THREEOFAKIND & handtype: s+=' THREEOFAKIND'
        if TWOPAIR & handtype: s+=' TWOPAIR'
        if ONEPAIR & handtype: s+=' PAIR'
        if CRAP & handtype: s+=' CRAP'
        if CARDS & handtype: s+=' CARDS'
        if OVERPAIR & handtype: s+=' OVERPAIR'
        if FLUSHDRAW & handtype: s+=' FLUSHDRAW'
        if STRAIGHTDRAW & handtype: s+=' STRAIGHTDRAW'
        if FIRSTVALUE & handtype: s+=' w/ %s'%cvt_to_rankstring((FIRSTVALUE & handtype)>>4)
        if SECONDVALUE & handtype: s+=', %s'%cvt_to_rankstring((SECONDVALUE & handtype)>>8)
        if TOPKICKER & handtype: s+=', %s kicker'%cvt_to_rankstring(TOPKICKER & handtype)
    return s[1:]

def format_pokerval(pokerval):
    s=''
    for bit in (31,30,29,28,27,26,25,24):
        s += str(int(pokerval & (2**bit)>0))
    s+=' '+hex(0x000FFFFF&pokerval)
    if STRAIGHTFLUSH & pokerval: s+=' STRAIGHTFLUSH'
    if FOUROFAKIND & pokerval: s+=' FOUROFAKIND'
    if FULLHOUSE & pokerval: s+=' FULLHOUSE'
    if FLUSH & pokerval: s+=' FLUSH'
    if STRAIGHT & pokerval: s+=' STRAIGHT'
    if THREEOFAKIND & pokerval: s+=' THREEOFAKIND'
    if TWOPAIR & pokerval: s+=' TWOPAIR'
    if ONEPAIR & pokerval: s+=' ONEPAIR'

    return s

def cvt_to_rank(i):
    """ Convert a thing to a rank, int from 2-14. """
    if type(i) is int:
        if i>14 or i<2:
            return i
        else:
            raise "problem in converting to rank",i
    elif type(i) is str:
        i = i.upper()
        rank={}
        rank['A']=14
        rank['K']=13
        rank['Q']=12
        rank['J']=11
        rank['T']=10
        try:
            return rank[i]
        except:
            #print type(i)
            return ord(i)-ord('0')

def cvt_to_rankstring(i):
    """ Convert a number to a rankstring, like K or Q or T or 8. """
    try:
        if type(i) is int:
            ranks = "TJQKAX"
            if i==0:
                return '?'
            elif i<10:
                return str(i)
            elif i<=15:
                return ranks[i-10]
            else:
                raise ValueError
    except:
        raise ValueError("wtf is that? that's not a legal rank: %d!"%i)

def cvt_to_suit(i):
	if i=='c': return 1
	elif i=='d': return 2
	elif i=='h': return 3
	elif i=='s': return 4
	else:
		raise ValueError("illegal suit: %s"%i)

def cvt_to_suitstring(i):
    """ Convert a number to a suitstring, h,s,d, or c. """
    try:
        if type(i) is int:
            ranks = "?cdhs"
            if i<5 and i>=0:
                return ranks[i]
            elif i==15:
                return 'X'
            else:
                raise ValueError
    except ValueError:
        raise ValueError("wtf is that? that's not a legal suit: %d!"%i)
    except:
        import traceback
        raise str(traceback.format_exc())

def format_cards(cards,minimal=False):
    """ Prettyprint some cards in a list/tuple. """
    if cards is None or len(cards)==0:
        return "<None>"

    ### make sure it's a list...
    if type(cards[0]) is int:
        cards = [cards,]
    if minimal:
        s=''
    else:
        s='<'
    if type(cards[0]) is int:
        cards = [cards,]
    for c in cards:
        try:
            if minimal:
                s += cvt_to_rankstring(c[0]) + cvt_to_suitstring(c[1])
            else:
                s += cvt_to_rankstring(c[0]) + cvt_to_suitstring(c[1]) + ' '
        except TypeError:
            raise TypeError("unsubscriptable: c=%s"%c)
    if minimal:
        return s
    else:
        return s[0:-1]+'>'

def cvt_to_cards(cardstrings):
    """ make a list of cards like ["As","Kh"] into card format """
    if cardstrings is None or len(cardstrings)==0:
        return []

    cards = []
    for cardstring in (cardstrings):
        cards.append((cvt_to_rank(cardstring[0]),cvt_to_suit(cardstring[1])))

    return cards

if __name__=='__main__':
    unittest_rotate_to_start_with()
