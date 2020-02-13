import partitura
import partitura.score as score
from lxml import etree
from partitura.utils.generic import partition
from partitura.utils.music import estimate_symbolic_duration
import sys

def extendKey(dictOfLists, key, value):
    if key in dictOfLists.keys():
        if isinstance(value, list):
            dictOfLists[key].extend(value)
        else:
            dictOfLists[key].append(value)
    else:
        if isinstance(value, list):
            dictOfLists[key]=value
        else:
            dictOfLists[key]=[value]

autoBeaming = True


def calc_dur_dots_splitNotes_firstTempDur(note, measure):
    if measure=="pad":
        return [], None, None

    if isinstance(note, score.GraceNote):
        dur_dots,_,_ = calc_dur_dots_splitNotes_firstTempDur(note.main_note, measure)
        dur_dots = [(2*dur_dots[0][0], dur_dots[0][1])]
        return dur_dots, None, None

    note_duration = note.duration

    splitNotes = None

    if note.start.t+note.duration>measure.end.t:
        note_duration = measure.end.t - note.start.t
        splitNotes = []

    quarterDur = measure.start.quarter
    fraction = note_duration/quarterDur
    intPart = int(fraction)
    fracPart = fraction - intPart

    # calc digits of fraction in base2
    untiedDurations = []
    powOf_2 = 1

    while intPart>0:
        bit = intPart%2
        untiedDurations.insert(0,bit*powOf_2)
        intPart=intPart//2
        powOf_2*=2


    powOf_2 = 1/2

    while fracPart > 0:
        fracPart*=2
        bit = int(fracPart)
        fracPart-=bit
        untiedDurations.append(bit*powOf_2)
        powOf_2/=2


    dur_dots = []

    curr_dur = 0
    curr_dots = 0

    def addDD(dur_dots,dur,dots):
        dur_dots.append((int(4/dur),dots))

    for untiedDur in untiedDurations:
        if curr_dur!=0:
            if untiedDur==0:
                addDD(dur_dots, curr_dur, curr_dots)
                curr_dots=0
                curr_dur=0
            else:
                curr_dots+=1
        else:
            curr_dur = untiedDur

    if curr_dur!=0:
        addDD(dur_dots, curr_dur, curr_dots)

    firstTempDur = int(untiedDurations[0]*quarterDur)

    return dur_dots,splitNotes, firstTempDur



def insertElem_check(t, inbetweenNotesElems):
    for ine in inbetweenNotesElems:
        if ine.elem!=None and ine.elem.start.t<=t:
            return True

    return False



def errorPrint(*list_errorMsg):
    for msg in list_errorMsg:
        print(msg)

    sys.exit()

def partition_handleNone(func, iter, partitionAttrib):
    p = partition(func,iter)
    newKey = None

    if None in p.keys():
        #errorPrint("PARTITION ERROR: some elements of set do not have partition attribute \""+partitionAttrib+"\"")

        # for testing purposes, introduce phantom staff, however, return to error when done testing
        newKey = 1

        for k in p.keys():
            if k!=None and k>newKey:
                newKey=k
        p[newKey]=p[None]
        del p[None]

    return p

def addChild(parent,childName):
    return etree.SubElement(parent,childName)

def setAttributes(elem, *list_attrib_val):
    for attrib_val in list_attrib_val:
        elem.set(attrib_val[0],str(attrib_val[1]))

def attribsOf_keySig(ks):
    key = ks.name
    pname = key[0].lower()
    mode = "major"

    if len(key)==2:
        mode="minor"

    fifths = str(abs(ks.fifths))

    if ks.fifths<0:
        fifths+="f"
    elif ks.fifths>0:
        fifths+="s"

    return fifths, mode, pname

def firstInstances_perPart(cls, parts, start=score.TimePoint(0), end=score.TimePoint(1)):
    if not isinstance(start, list):
        start = [start]*len(parts)
    else:
        assert len(parts)==len(start), "ERROR at firstInstances_perPart: start times are given as list with different size to parts list"

    if not isinstance(end, list):
        end = [end]*len(parts)
    else:
        assert len(parts)==len(end), "ERROR at firstInstances_perPart: end times are given as list with different size to parts list"

    instances_perPart=[]

    nonEmpty = False

    for i,p in enumerate(parts):
        s = start[i]
        e = end[i]
        instances = list(p.iter_all(cls,s,e))

        if len(instances)==0:
            instances_perPart.append([])
            continue

        nonEmpty = True
        t = min(instances, key=lambda i:i.start.t).start.t
        instances_perPart.append([i for i in instances if t==i.start.t])

    if nonEmpty:
        return instances_perPart

    return []

def firstInstance_perPart(cls, parts, start=score.TimePoint(0), end=score.TimePoint(1)):
    fispp = firstInstances_perPart(cls, parts, start, end)

    fipp = []

    for i,fis in enumerate(fispp):
        if len(fis)==0:
            fipp.append(None)
        elif len(fis)==1:
            fipp.append(fis[0])
        else:
            errorPrint("Part "+parts[i].name,
            "ID "+parts[i].id,
            "has more than one instance of "+str(cls)+" at beginning t=0, but there should only be a single one")

    return fipp

def firstInstances(cls, part, start=score.TimePoint(0), end=score.TimePoint(1)):
    fis = firstInstances_perPart(cls, [part], start, end)

    if len(fis)==0:
        return []

    return fis[0]

def firstInstance(cls, part, start=score.TimePoint(0), end=score.TimePoint(1)):
    fi = firstInstance_perPart(cls, [part], start, end)

    if len(fi)==0:
        return None

    return fi[0]


def commonSignature(cls, sig_eql, parts, currentMeasures=None):
    sigs = None
    if currentMeasures!=None:
        sigs = firstInstance_perPart(cls, parts, start=[cm.start for cm in currentMeasures], end=[cm.end for cm in currentMeasures])
    else:
        sigs = firstInstance_perPart(cls, parts)

    if sigs==None or len(sigs)==0 or None in sigs:
        return None

    commonSig = sigs.pop()

    for sig in sigs:
        if sig.start.t!=commonSig.start.t or not sig_eql(sig, commonSig):
            return None

    return commonSig





# parts = [score.Part("P0","Test"), score.Part("P1","Test"), score.Part("P2","Test")]
#
#
# parts[0].set_quarter_duration(0,2)
# parts[0].add(score.KeySignature(0,"major"),start=0)
# parts[0].add(score.TimeSignature(4,4),start=0)
# parts[0].add(score.Tempo(90),start=0)
#
# parts[1].add(score.KeySignature(0,"major"),start=0)
# parts[1].set_quarter_duration(0,8)
# parts[1].add(score.TimeSignature(3,4),start=0)
# parts[1].add(score.Tempo(120),start=0)
#
# parts[2].set_quarter_duration(0,8)
# parts[2].add(score.KeySignature(0,"major"),start=0)
# parts[2].add(score.TimeSignature(4,4),start=0)
# parts[2].add(score.Tempo(90),start=0)
#
# parts[0].add(score.Clef(sign="G",line=2, octave_change=0, number=1),start=0)
# parts[1].add(score.Clef(sign="F",line=4, octave_change=0, number=2),start=0)
# parts[2].add(score.Clef(sign="G",line=2, octave_change=1, number=3),start=0)
#
#
#
# parts[0].add(score.Note(id="n0s2",step="C",octave=4, staff=1, voice=1),start=0,end=5)
# parts[0].add(score.Note(id="n2s2",step="G",octave=4, staff=1, voice=1),start=5,end=6)
# parts[0].add(score.Note(id="n3s2",step="E",octave=4, staff=1, voice=1),start=6,end=7)
# parts[0].add(score.Note(id="n4s2",step="F",octave=4, staff=1, voice=1),start=7,end=9)
# parts[0].add(score.Note(id="n5s2",step="D",octave=4, staff=1, voice=1),start=9,end=10)
# parts[0].add(score.Note(id="n6s2",step="A",octave=4, staff=1, voice=1),start=10,end=16)
#
# parts[2].add(score.Note(id="n0s22",step="E",octave=4, staff=3, voice=1),start=0,end=5*4)
# parts[2].add(score.Note(id="n2s22",step="B",octave=4, staff=3, voice=1),start=5*4,end=6*4)
# parts[2].add(score.Note(id="n3s22",step="G",octave=4, staff=3, voice=1),start=6*4,end=7*4)
# parts[2].add(score.Note(id="n4s22",step="A",octave=4, staff=3, voice=1),start=7*4,end=8*4)
#
# parts[0].add(score.Note(id="n0s2+16",step="C",octave=4, staff=1, voice=1),start=0+16,end=5+16)
# parts[0].add(score.Note(id="n2s2+16",step="G",octave=4, staff=1, voice=1),start=5+16,end=6+16)
# parts[0].add(score.Note(id="n3s2+16",step="E",octave=4, staff=1, voice=1),start=6+16,end=7+16)
# parts[0].add(score.Note(id="n4s2+16",step="F",octave=4, staff=1, voice=1),start=7+16,end=9+16)
# parts[0].add(score.Note(id="n5s2+16",step="D",octave=4, staff=1, voice=1),start=9+16,end=10+16)
# parts[0].add(score.Note(id="n6s2+16",step="A",octave=4, staff=1, voice=1),start=10+16,end=16+16)
#
# parts[2].add(score.Note(id="n0s22+16*4",step="E",octave=4, staff=3, voice=1),start=0+16*4,end=5*4+16*4)
# parts[2].add(score.Note(id="n2s22+16*4",step="B",octave=4, staff=3, voice=1),start=5*4+16*4,end=6*4+16*4)
# parts[2].add(score.Note(id="n3s22+16*4",step="G",octave=4, staff=3, voice=1),start=6*4+16*4,end=7*4+16*4)
# parts[2].add(score.Note(id="n4s22+16*4",step="A",octave=4, staff=3, voice=1),start=7*4+16*4,end=8*4+16*4)
#
# def conv(fraction, qd):
#     return int(fraction*qd)
#
# qd = 8
# t1 = 0
# t2 = conv(9/8, qd)
# parts[1].add(score.Note(id="n0",step="C",octave=2, staff=2, voice=1),start=t1,end=t2)
# t1 = t2
# t2 = conv(9/8, qd) + t1
# parts[1].add(score.Note(id="n2",step="E",octave=2, staff=2, voice=1),start=t1,end=t2)
# t1 = t2
# t2 = conv(3/8, qd) + t1
# parts[1].add(score.Note(id="n3",step="G",octave=2, staff=2, voice=1),start=t1,end=t2)
# t1 = t2
# t2 = conv(9/8, qd) + t1
# parts[1].add(score.Note(id="n4",step="D",octave=2, staff=2, voice=1),start=t1,end=t2)
# t1 = t2
# t2 = conv(9/8, qd) + t1
# parts[1].add(score.Note(id="n5",step="F",octave=2, staff=2, voice=1),start=t1,end=t2)
# t1 = t2
# t2 = conv(9/8, qd) + t1
# parts[1].add(score.Note(id="n6",step="C",octave=3, staff=2, voice=1),start=t1,end=t2)
# score.add_measures(parts[0])
# score.add_measures(parts[1])
# score.add_measures(parts[2])
#
# score.tie_notes(parts[0])
# score.tie_notes(parts[1])
# test case blues lick
# part = score.Part("P0","Test")
# part.set_quarter_duration(0,10)
# part.add(score.KeySignature(-3,"minor"),start=0)
# part.add(score.TimeSignature(6,8),start=0)
# part.add(score.Clef(sign="F",line=4, octave_change=0, number=1),start=0)
# part.add(score.Clef(sign="G",line=2, octave_change=0, number=2),start=0)
# n0 = score.Note(id="n0",step="C",octave=2,voice=1, staff=1)
# n1 =score.Note(id="n1",step="E",octave=2,voice=1, staff=1, alter=-1)
# n2 =score.Note(id="n2",step="D",octave=2,voice=1, staff=1)
# part.add(n0,start=0,end=5)
# part.add(n1,start=5,end=10)
# part.add(n2,start=10,end=15)
# n0q = score.Note(id="n0q",step="G",octave=2,voice=1, staff=1)
# n1q =score.Note(id="n1q",step="G",octave=2,voice=1, staff=1)
# n2q =score.Note(id="n2q",step="G",octave=2,voice=1, staff=1)
# part.add(n0q,start=0,end=5)
# part.add(n1q,start=5,end=10)
# part.add(n2q,start=10,end=15)
# part.add(score.Note(id="n3",step="C",octave=2,voice=1, staff=1),start=15,end=40)
# n0s2 = score.Note(id="n0s2",step="C",octave=4,voice=1, staff=2)
# n1s2 =score.Note(id="n1s2",step="E",octave=4,voice=1, staff=2, alter=-1)
# n2s2 =score.Note(id="n2s2",step="D",octave=4,voice=1, staff=2)
# part.add(n0s2,start=0,end=5)
# part.add(n1s2,start=5,end=10)
# part.add(n2s2,start=10,end=15)
# part.add(score.Slur(n0s2,n2s2),start=0)
# part.add(score.Note(id="n3s2",step="C",octave=4,voice=1, staff=2),start=15,end=40)
#
# score.add_measures(part)
# score.tie_notes(part)
# parts=[part]



# part = score.Part("P0", "Test")
# part.set_quarter_duration(0,2)
# part.add(score.KeySignature(-3,"minor"),start=0)
# part.add(score.TimeSignature(2,4),start=0)
# part.add(score.Clef(sign="F",line=4, octave_change=0, number=1),start=0)
#
# n0 = score.Note(id="n0",step="C",octave=4,voice=1, staff=1)
# n1 = score.Note(id="n1",step="C",octave=4,voice=1, staff=1)
# n2 = score.Note(id="n2",step="C",octave=4,voice=1, staff=1)
# n3 = score.Note(id="n3",step="C",octave=4,voice=1, staff=1)
# g = score.GraceNote(id="g", step="B", octave=3, voice=1, staff=1, grace_type='appoggiatura', steal_proportion=0.25)
# g.grace_next = n3
#
# part.add(n0,start=0,end=1)
# part.add(n1,start=1,end=2)
# part.add(n2,start=2,end=3)
# part.add(g,start=3,end=3)
# part.add(n3,start=3,end=4)
#
# b1=score.Beam(id="b1")
# b2=score.Beam(id="b2")
#
# b1.append(n0)
# b1.append(n1)
# b2.append(n2)
# b2.append(n3)
#
# part.add(b1,start=0,end=2)
# part.add(b2,start=2,end=4)
#
# score.add_measures(part)
#
# autoBeaming=False
#
# parts=part


part = score.Part("P0","Test")
part.set_quarter_duration(0,2)
part.add(score.TimeSignature(4,4),start=0,end=8)
part.add(score.Rest(id="r0",staff=1, voice=1),start=0,end=8)
part.add(score.TimeSignature(6,8),start=8,end=8+6)
part.add(score.Words("Oy",staff=1),start=4)
part.add(score.Rest(id="r1",staff=1, voice=1),start=8,end=8+6)
score.add_measures(part)



parts=[part]

# # testing crossing measures and tieing notes together
# part = score.Part("P0", "Test")
# part.set_quarter_duration(0,16)
# part.add(score.KeySignature(-3,"minor"),start=0)
# part.add(score.TimeSignature(4,4),start=0)
# part.add(score.Clef(sign="F",line=4, octave_change=0, number=1),start=0)
#
# part.add(score.Rest(id="r0",staff=1, voice=1),start=0,end=1)
#
# e = 4*16
#
# part.add(score.Note(id="n0",step="C",octave=2, staff=1, voice=1),start=1,end=e)
# part.add(score.Note(id="n2",step="G",octave=2, staff=1, voice=1),start=1,end=e)
# part.add(score.Note(id="n3",step="E",octave=3, staff=1, voice=1),start=1,end=e)
# part.add(score.Rest(id="r1",staff=1, voice=1),start=e,end=2*e)
#
# score.add_measures(part)
#
# parts = part

# using this feature?
# making ties then becomes about looking at the tiegroup tag of notes
# which is fine, however the sum of powers of 2 idea seems better than estimating symbolic duration
# without this feature, notes crossing measure boundaries have to be handled
#score.tie_notes(part)



# parts = partitura.load_musicxml("../../tests/data_examples/Three-Part_Invention_No_13_(fragment).xml", force_note_ids=True)
# #parts = partitura.load_musicxml("../../tests/data/musicxml/test_note_ties.xml", force_note_ids=True)
#
#
# part = parts
#
# qd=part.quarter_durations()[0][1]
#
# part.add(score.Clef(sign="F",line=4, octave_change=0, number=2), start=int(qd*(2+1/4)))
# part.add(score.KeySignature(-3,"minor"),start=int(qd*(2+1/4)))
#
# partitura.render(parts)
#
# parts=[part]





nameSpace = "http://www.music-encoding.org/ns/mei"

xmlIdString = "{http://www.w3.org/XML/1998/namespace}id"



mei = etree.Element("mei")

meiHead=addChild(mei,"meiHead")
music = addChild(mei,"music")



meiHead.set("xmlns",nameSpace)
fileDesc = addChild(meiHead,"fileDesc")
titleStmt=addChild(fileDesc,"titleStmt")
pubStmt=addChild(fileDesc,"pubStmt")
title=addChild(titleStmt,"title")
title.set("type","main")
title.text="TEST1000"

body = addChild(music,"body")
mdiv=addChild(body,"mdiv")
mei_score=addChild(mdiv,"score")

scoreDef = addChild(mei_score,"scoreDef")



staves_perPart=[]

for p in parts:
    staves_perPart.append([])
    for thing in p.iter_all(object, include_subclasses=True):
        val = getattr(thing,"staff",None)

        if val is not None and not val in staves_perPart[-1]:
            staves_perPart[-1].append(val)



measures = [list(parts[0].iter_all(score.Measure))]
paddingRequired = False
maxLength = len(measures[0])
for i in range(1,len(parts)):
    m = list(parts[i].iter_all(score.Measure))

    if len(m) > maxLength:
        maxLength = len(m)

    if not paddingRequired:
        paddingRequired = (len(m)!=len(measures[0]))

    measures.append(m)

# for mp in measures:
#     print("|",end="")
#     for m in mp:
#         print(m.start.t,"-",m.end.t,"|",end="")
#     print("")


def verticalSlice(list_2d, index):
    vslice = []

    for list_1d in list_2d:
        vslice.append(list_1d[index])

    return vslice

startingMeasures = verticalSlice(measures,0)
commonKeySig = commonSignature(score.KeySignature, lambda ks1, ks2: ks1.name==ks2.name and ks1.fifths==ks2.fifths, parts, startingMeasures)

def timeSig_eql(ts1,ts2):
    return ts1.beats==ts2.beats and ts1.beat_type==ts2.beat_type

commonTimeSig = commonSignature(score.TimeSignature, timeSig_eql,parts, startingMeasures)





if commonKeySig!=None:
    fifths, mode, pname = attribsOf_keySig(commonKeySig)

    setAttributes(scoreDef,("key.sig",fifths),("key.mode", mode),("key.pname",pname))

if commonTimeSig!=None:
    setAttributes(scoreDef,("meter.count",commonTimeSig.beats),("meter.unit",commonTimeSig.beat_type))

section = addChild(mei_score,"section")

# might want to count staff numbers during processing and update staffGrp if count isn't consistent with clefs
staffGrp = addChild(scoreDef,"staffGrp")



clefs_perPart=firstInstances_perPart(score.Clef, parts)

def idx(len_obj):
    return range(len(len_obj))

for i in idx(clefs_perPart):
    clefs_perPart[i] = partition_handleNone(lambda c:c.number, clefs_perPart[i], "number")

staves_sorted = [s for staves in staves_perPart for s in staves]
staves_sorted.sort()

def attribsOf_Clef(clef):
    if clef.octave_change!=None and clef.octave_change!=0:
        place = "above"

        if clef.octave_change<0:
            place="below"

        return clef.sign, clef.line, 1+7*abs(clef.octave_change), place

    return clef.sign, clef.line

def create_staffDef(staffGrp, clef):
    staffDef = addChild(staffGrp,"staffDef")

    attribs = attribsOf_Clef(clef)
    setAttributes(staffDef,("n",clef.number),("lines",5),("clef.shape",attribs[0]),("clef.line",attribs[1]))
    if len(attribs)==4:
        setAttributes(staffDef,("clef.dis",attribs[2]),("clef.dis.place",attribs[3]))


def create_staffDef_safe(staffGrp, c):
    clef = c[0]
    assert len(c)==1, "ERROR at staffDef creation: Staff "+str(clef.number)+" starts with more than 1 clef at t=0"
    create_staffDef(staffGrp, clef)

if len(clefs_perPart)==0 and len(staves_sorted)==0:
    create_staffDef(staffGrp, score.Clef(sign="G",line=2, number=1, octave_change=0))
else:
    for s in staves_sorted:
        clefs = None

        for cs in clefs_perPart:
            if s in cs.keys():
                clefs = cs
                break

        if clefs!=None:
            c = clefs[s]
            create_staffDef_safe(staffGrp, c)

            del clefs[s]
        else:
            create_staffDef(staffGrp, score.Clef(sign="G",line=2, number=s, octave_change=0))

    for i, clefs in enumerate(clefs_perPart):
        staves_perPart[i].extend(clefs.keys())
        staves_sorted.extend(clefs.keys())
        for c in clefs.values():
            create_staffDef_safe(staffGrp, c)
    staves_sorted.sort()

measuresAreAligned = True
if paddingRequired:
    cursors = [0]*len(measures)
    tempii = [None]*len(measures)

    while measuresAreAligned:
        compareMeasures = {}
        for i,m in enumerate(measures):
            if cursors[i]<len(m):
                compareMeasures[i]=m[cursors[i]]
                cursors[i]+=1


        if len(compareMeasures)==0:
            break

        compM_keys = list(compareMeasures.keys())

        new_tempii = firstInstance_perPart(score.Tempo, [p for i, p in enumerate(parts) if i in compM_keys], start=[cm.start for cm in compareMeasures.values()], end=[cm.end for cm in compareMeasures.values()])

        if len(new_tempii)==0:
            for k in compM_keys:
                new_tempii.append(tempii[k])
        else:
            for i,nt in enumerate(new_tempii):
                if nt==None:
                    new_tempii[i]=tempii[compM_keys[i]]
                else:
                    tempii[compM_keys[i]]=nt

        def normDur(m):
            return (m.end.t-m.start.t)//m.start.quarter

        rep_i=0
        while rep_i<len(new_tempii) and new_tempii[rep_i]==None:
            rep_i+=1

        if rep_i==len(new_tempii):
            continue

        rep_dur = normDur(compareMeasures[compM_keys[rep_i]])*new_tempii[rep_i].bpm

        for i in range(rep_i+1,len(compM_keys)):
            nt = new_tempii[i]

            if nt==None:
                continue

            m = compareMeasures[compM_keys[i]]
            dur = normDur(m)*new_tempii[i].bpm

            if dur!=rep_dur:
                measuresAreAligned=False
                break

if measuresAreAligned:
    timeOffset = [0]*len(measures)

    measurePad = score.Measure

    if paddingRequired:
        for i, mp in enumerate(measures):
            ii=len(mp)
            timeOffset[i]=mp[ii-1].end.t
            while ii<maxLength:
                mp.append("pad")
                ii+=1

    notes_lastMeasure_perStaff = {}
    autoRestCount = 0

    for measure_i,_ in enumerate(measures[0]):
        measure=addChild(section,"measure")
        setAttributes(measure,("n",measure_i))



        notes_nextMeasure_perStaff={}
        ties_perStaff = {}
        notes_withinMeasure_perStaff = notes_lastMeasure_perStaff
        clefs_withinMeasure_perStaff = {}
        keySigs_withinMeasure_perStaff = {}
        timeSigs_withinMeasure_perStaff = {}
        measure_perStaff = {}
        slurs_withinMeasure = []
        dirs_withinMeasure=[]
        tuplets_withinMeasure_perStaff = {}

        for part_i, part in enumerate(parts):
            m = measures[part_i][measure_i]



            def padMeasure(s, measure_perStaff, notes_withinMeasure_perStaff, autoRestCount):
                measure_perStaff[s]="pad"
                r = score.Rest(id="pR"+str(autoRestCount), voice=1)
                r.start = score.TimePoint(0)
                r.end = r.start

                extendKey(notes_withinMeasure_perStaff, s, r)
                return autoRestCount+1

            if m=="pad":
                for s in staves_perPart[part_i]:
                    autoRestCount = padMeasure(s, measure_perStaff, notes_withinMeasure_perStaff, autoRestCount)

                continue



            def cls_withinMeasure(part, cls, measure, incl_subcls=False):
                return part.iter_all(cls, measure.start, measure.end, include_subclasses=incl_subcls)

            clefs_withinMeasure_perStaff_perPart = partition_handleNone(lambda c:c.number, cls_withinMeasure(part, score.Clef, m),"number")
            keySigs_withinMeasure = list(cls_withinMeasure(part,score.KeySignature, m))
            timeSigs_withinMeasure = list(cls_withinMeasure(part, score.TimeSignature, m))
            slurs_withinMeasure.extend(cls_withinMeasure(part, score.Slur, m))

            beat_map = part.beat_map

            for w in cls_withinMeasure(part, score.Words, m):
                tstamp=beat_map(w.start.t)-beat_map(m.start.t)+1
                dirs_withinMeasure.append((tstamp,w))


            notes_withinMeasure_perStaff_perPart = partition_handleNone(lambda n:n.staff, cls_withinMeasure(part,score.GenericNote, m, True), "staff")

            for s in staves_perPart[part_i]:
                keySigs_withinMeasure_perStaff[s]=keySigs_withinMeasure
                timeSigs_withinMeasure_perStaff[s]=timeSigs_withinMeasure

                if s not in notes_withinMeasure_perStaff_perPart.keys():
                    autoRestCount = padMeasure(s, measure_perStaff, notes_withinMeasure_perStaff, autoRestCount)

            for s in notes_withinMeasure_perStaff_perPart.keys():
                extendKey(notes_withinMeasure_perStaff, s, notes_withinMeasure_perStaff_perPart[s])
                measure_perStaff[s]=m

            for s in clefs_withinMeasure_perStaff_perPart.keys():
                clefs_withinMeasure_perStaff[s]=clefs_withinMeasure_perStaff_perPart[s]

        for s in staves_sorted:
            staff=addChild(measure,"staff")

            setAttributes(staff,("n",s))

            notes_withinMeasure_perStaff_perVoice = partition_handleNone(lambda n:n.voice, notes_withinMeasure_perStaff[s], "voice")

            ties_perStaff_perVoice={}

            m = measure_perStaff[s]


            for voice,notes in notes_withinMeasure_perStaff_perVoice.items():
                layer=addChild(staff,"layer")

                setAttributes(layer,("n",voice))

                ties={}

                notes_partition=partition_handleNone(lambda n:n.start.t, notes, "start.t")

                chords = []



                for t in sorted(notes_partition.keys()):
                    ns = notes_partition[t]

                    if len(ns)>1:
                        type_partition = partition_handleNone(lambda n: isinstance(n,score.GraceNote),ns,"isGraceNote")

                        if True in type_partition.keys():
                            gns = type_partition[True]

                            gn_chords=[]

                            def scanBackwards(gns):
                                start = gns.pop(0)

                                while isinstance(start.grace_prev, score.GraceNote):
                                    start = start.grace_prev

                                    assert start in gns, "ERROR at GraceNote-proc scanBackwards: Connected GraceNotes don't share same staff or voice or starting time"

                                    gns.remove(start)

                                return start

                            start = scanBackwards(gns)

                            while isinstance(start, score.GraceNote):
                                gn_chords.append([start])
                                start = start.grace_next

                            while len(gns)>0:
                                start = scanBackwards(gns)

                                i=0
                                while isinstance(start, score.GraceNote):
                                    assert i<len(gn_chords), "ERROR at GraceNote-forward scanning: Difference in lengths of grace note sequences for different chord notes"

                                    gn_chords[i].append(start)
                                    start = start.grace_next
                                    i+=1

                                assert i==len(gn_chords), "ERROR at GraceNote-forward scanning: Difference in lengths of grace note sequences for different chord notes"

                            for gnc in gn_chords:
                                chords.append(gnc)

                        assert False in type_partition.keys(), "ERROR at ChordNotes-grouping: GraceNotes detected without additional regular Notes at same time"
                        regNotes =type_partition[False]
                        rep = regNotes[0]

                        for i in range(1,len(regNotes)):
                            n = regNotes[i]
                            if n.duration!=rep.duration:
                                errorPrint("In staff "+str(s)+",",
                                "in measure "+str(m.number)+",",
                                "for voice "+str(voice)+",",
                                "2 notes start at time "+str(n.start.t)+",",
                                "but have different durations, namely "+n.id+" has duration "+str(n.duration)+" and "+rep.id+" has duration "+str(rep.duration),
                                "change to same duration for a chord or change voice of one of the notes for something else")
                            elif rep.beam!=n.beam:
                                print("WARNING: notes within chords don't share the same beam",
                                "specifically note "+str(rep)+" has beam "+str(rep.beam),
                                "and note "+str(n)+" has beam "+str(n.beam),
                                "export still continues though")

                        chords.append(regNotes)
                    else:
                        chords.append(ns)





                def handleBeam(openUp, layer):
                    parent = layer

                    if openUp:
                        parent = addChild(layer,"beam")

                    return openUp, parent


                openBeam, parent = handleBeam(False,layer)

                next_dur_dots, next_splitNotes, next_firstTempDur = calc_dur_dots_splitNotes_firstTempDur(chords[0][0],m)

                class InbetweenNotesElement:
                    __slots__ = ["name","attribNames","attribValsOf","container","i","elem"]

                    def __init__(self, name, attribNames, attribValsOf, container_dict, staff, measure_i, skipIndex):
                        self.name = name
                        self.attribNames = attribNames
                        self.attribValsOf = attribValsOf

                        self.i=0
                        self.elem=None

                        if staff in container_dict.keys():
                            self.container = container_dict[staff]
                            if measure_i==0:
                                if len(self.container)>skipIndex:
                                    self.elem = self.container[skipIndex]
                            else:
                                if len(self.container)>0:
                                    self.elem = self.container[0]
                        else:
                            self.container=[]




                inbetweenNotesElements = [
                    InbetweenNotesElement("clef", ["shape","line","dis","dis.place"], attribsOf_Clef, clefs_withinMeasure_perStaff, s, measure_i,1),
                    InbetweenNotesElement("keySig", ["sig","mode","pname","sig.showchange"], (lambda ks: attribsOf_keySig(ks)+("true",)), keySigs_withinMeasure_perStaff, s, measure_i, int(commonKeySig!=None)),
                    InbetweenNotesElement("meterSig", ["count","unit"], lambda ts: (ts.beats, ts.beat_type), timeSigs_withinMeasure_perStaff, s, measure_i, int(commonTimeSig!=None))
                ]

                for chord_i, chordNotes in enumerate(chords):
                    rep = chordNotes[0]

                    for ine in inbetweenNotesElements:
                        if insertElem_check(rep.start.t, [ine]):
                            # note should maybe be split according to keysig or clef etc insertion time, right now only beaming is disrupted
                            if openBeam and autoBeaming:
                                openBeam, parent = handleBeam(False,layer)

                            xmlElem = addChild(parent, ine.name)
                            attribVals = ine.attribValsOf(ine.elem)

                            assert len(ine.attribNames)>=len(attribVals), "ERROR at insertion of inbetweenNotesElements: there are more attribute values than there are attribute names for xml element "+ine.name

                            for nv in zip(ine.attribNames[:len(attribVals)], attribVals):
                                setAttributes(xmlElem,nv)

                            if ine.i+1>=len(ine.container):
                                ine.elem = None
                            else:
                                ine.i+=1
                                ine.elem = ine.container[ine.i]


                    def nextRep(chords,chord_i):
                        return chords[chord_i+1][0]

                    dur_dots,splitNotes, firstTempDur = next_dur_dots, next_splitNotes, next_firstTempDur
                    # hack right now, don't need to check every iteration, good time to factor out inside of loop
                    if chord_i < len(chords)-1:
                        next_dur_dots, next_splitNotes, next_firstTempDur = calc_dur_dots_splitNotes_firstTempDur(nextRep(chords,chord_i), m)



                    if isinstance(rep,score.Note):
                        if not isinstance(rep, score.GraceNote):
                            if autoBeaming:
                                # for now all notes are beamed, however some rules should be obeyed there, see Note Beaming and Grouping

                                # check to close beam
                                if openBeam and dur_dots[0][0]<8:
                                    openBeam, parent = handleBeam(False,layer)
                                # check to open beam
                                elif not openBeam and dur_dots[0][0]>=8:
                                    # open beam if there are multiple "consecutive notes" which don't get interrupted by some element
                                    if len(dur_dots)>1 and not insertElem_check(rep.start.t+firstTempDur, inbetweenNotesElements):
                                        openBeam, parent = handleBeam(True,layer)
                                    # open beam if there is just a single note that is not the last one in measure and next note in measure fits in beam as well, without getting interrupted by some element
                                    elif len(dur_dots)<=1 and chord_i<len(chords)-1 and next_dur_dots[0][0]>=8 and not insertElem_check(nextRep(chords,chord_i).start.t, inbetweenNotesElements):
                                        openBeam, parent = handleBeam(True,layer)
                            elif openBeam and rep.beam!=chords[chord_i-1][0].beam and not isinstance(chords[chord_i-1][0],score.GraceNote):
                                openBeam, parent = handleBeam(False,layer)

                            if not autoBeaming and not openBeam and rep.beam!=None:
                                openBeam, parent = handleBeam(True,layer)

                        def conditional_gracify(elem, rep):
                            if isinstance(rep,score.GraceNote):
                                grace = "unacc"

                                if rep.grace_type == "appoggiatura":
                                    grace = "acc"

                                setAttributes(elem,("grace",grace))

                                if rep.steal_proportion != None:
                                    setAttributes(elem,("grace.time",str(rep.steal_proportion*100)+"%"))

                        if len(chordNotes)>1:
                            chord = addChild(parent,"chord")
                            setAttributes(chord,("dur",dur_dots[0][0]),("dots",dur_dots[0][1]))

                            conditional_gracify(chord, rep)

                            for n in chordNotes:
                                note=addChild(chord,"note")
                                setAttributes(note,(xmlIdString,n.id),("pname",n.step.lower()),("oct",n.octave))
                        else:
                            note=addChild(parent,"note")
                            setAttributes(note,(xmlIdString,rep.id),("pname",rep.step.lower()),("oct",rep.octave),("dur",dur_dots[0][0]),("dots",dur_dots[0][1]))

                            conditional_gracify(note,rep)

                        if len(dur_dots)>1:
                            for n in chordNotes:
                                ties[n.id]=[n.id]

                            def create_splitUpNotes(chordNotes, i, parent, dur_dots, ties, xmlIdString, rep):
                                if len(chordNotes)>1:
                                    chord = addChild(parent,"chord")
                                    setAttributes(chord,("dur",dur_dots[i][0]),("dots",dur_dots[i][1]))

                                    for n in chordNotes:
                                        note=addChild(chord,"note")

                                        id = n.id+"-"+str(i)

                                        ties[n.id].append(id)

                                        setAttributes(note,(xmlIdString,id),("pname",n.step.lower()),("oct",n.octave))
                                else:
                                    note=addChild(parent,"note")

                                    id = rep.id+"-"+str(i)

                                    ties[rep.id].append(id)

                                    setAttributes(note,(xmlIdString,id),("pname",rep.step.lower()),("oct",rep.octave),("dur",dur_dots[i][0]),("dots",dur_dots[i][1]))

                            for i in range(1,len(dur_dots)-1):
                                if not openBeam and dur_dots[i][0]>=8:
                                    openBeam, parent = handleBeam(True,layer)

                                create_splitUpNotes(chordNotes, i,parent,dur_dots,ties,xmlIdString, rep)

                            create_splitUpNotes(chordNotes, len(dur_dots)-1,parent,dur_dots,ties,xmlIdString, rep)


                        if splitNotes!=None:


                            for n in chordNotes:
                                splitNotes.append(score.Note(n.step,n.octave, id=n.id+"s"))



                            if len(dur_dots)>1:
                                for n in chordNotes:
                                    ties[n.id].append(n.id+"s")
                            else:
                                for n in chordNotes:
                                    ties[n.id]=[n.id, n.id+"s"]

                        for n in chordNotes:
                            if n.tie_next!=None:
                                if n.id in ties.keys():
                                    ties[n.id].append(n.tie_next.id)
                                else:
                                    ties[n.id]=[n.id, n.tie_next.id]

                    elif isinstance(rep,score.Rest):
                        if splitNotes!=None:
                            splitNotes.append(score.Rest(id=rep.id+"s"))

                        if m=="pad" or m.start.t == rep.start.t and m.end.t == rep.end.t:
                            rest = addChild(layer,"mRest")

                            setAttributes(rest,(xmlIdString,rep.id))
                        else:
                            rest = addChild(layer,"rest")

                            setAttributes(rest,(xmlIdString,rep.id),("dur",dur_dots[0][0]),("dots",dur_dots[0][1]))

                            if len(dur_dots)>1:
                                for i in range(1,len(dur_dots)):
                                    rest=addChild(layer,"rest")

                                    id = rep.id+str(i)

                                    setAttributes(rest,(xmlIdString,id),("dur",dur_dots[i][0]),("dots",dur_dots[i][1]))

                    if splitNotes!=None:
                        for sn in splitNotes:
                            sn.voice = rep.voice
                            sn.start = m.end
                            sn.end = score.TimePoint(rep.start.t+rep.duration)

                            if s in notes_nextMeasure_perStaff.keys():
                                notes_nextMeasure_perStaff[s].append(sn)
                            else:
                                notes_nextMeasure_perStaff[s]=[sn]


                ties_perStaff_perVoice[voice]=ties

            ties_perStaff[s]=ties_perStaff_perVoice



        notes_lastMeasure_perStaff = notes_nextMeasure_perStaff

        for slur in slurs_withinMeasure:
            s = addChild(measure,"slur")
            setAttributes(s, ("staff",slur.start_note.staff), ("startid","#"+slur.start_note.id), ("endid","#"+slur.end_note.id))

        for tstamp,word in dirs_withinMeasure:
            d = addChild(measure, "dir")
            setAttributes(d,("staff",word.staff),("tstamp",tstamp))
            d.text = word.text

#         for word in perPartIter(parts, score.Words, m.start, m.end):
#             w = addChild(measure,"dir")
#             setAttributes(w, ("staff",w.staff), ("tstamp",))

        for s,tps in ties_perStaff.items():

            for v,tpspv in tps.items():

                for ties in tpspv.values():

                    for i in range(len(ties)-1):
                        tie = addChild(measure, "tie")

                        setAttributes(tie, ("staff",s), ("startid","#"+ties[i]), ("endid","#"+ties[i+1]))







(etree.ElementTree(mei)).write("testResult.mei",pretty_print=True)

#print(etree.tostring(mei,pretty_print=True))
