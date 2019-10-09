#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This module contains methods for parsing matchfiles

TODO
----
* Add PerformanceTimeline?
* Allow for creating Notes and other elements from matchlines
"""
import re
import numpy as np
from fractions import Fraction

import logging
import warnings


__all__ = ['load_match']
LOGGER = logging.getLogger(__name__)

rational_pattern = re.compile('^([0-9]+)/([0-9]+)$')
double_rational_pattern = re.compile('^([0-9]+)/([0-9]+)/([0-9]+)$')
LATEST_VERSION = 5.0

PITCH_CLASSES = [('C', 'n'), ('C', '#'), ('D', 'n'), ('D', '#'), ('E', 'n'), ('F', 'n'),
                 ('F', '#'), ('G', 'n'), ('G', '#'), ('A', 'n'), ('A', '#'), ('B', 'n')]

PC_DICT = dict(zip(range(12), PITCH_CLASSES))

NOTE_NAMES = ['C', 'D', 'E', 'F', 'G', 'A', 'B']

LATEST_VERSION = 5.0

# Ignore enharmonic keys above A# Maj (no E# Maj!)
KEY_SIGNATURES = {0: ('C', 'A'), 1: ('G', 'E'), 2: ('D', 'B'), 3: ('A', 'F#'),
                  4: ('E', 'C#'), 5: ('B', 'G#'), 6: ('F#', 'D#'), 7: ('C#', 'A#'),
                  8: ('G#', 'E#'), 9: ('D#', 'B#'), 10: ('A#', 'F##'),
                  -1: ('F', 'D'), -2: ('Bb', 'G'), -3: ('Eb', 'C'), -4: ('Ab', 'F'),
                  -5: ('Db', 'Bb'), -6: ('Gb', 'Eb'), -7: ('Cb', 'Ab')}


class MatchError(Exception):
    pass


class FractionalSymbolicDuration(object):

    def __init__(self, numerator, denominator=1, tuple_div=None):

        self.numerator = numerator
        self.denominator = denominator
        self.tuple_div = tuple_div

    def __str__(self):

        if self.denominator == 1 and self.tuple_div is None:
            return str(self.numerator)
        else:
            if self.tuple_div is None:
                return '{0}/{1}'.format(self.numerator,
                                        self.denominator)
            else:
                return '{0}/{1}/{2}'.format(self.numerator,
                                            self.denominator,
                                            self.tuple_div)

    def __add__(self, sd):

        if isinstance(sd, int):
            sd = FractionalSymbolicDuration(sd, 1)

        dens = np.array([self.denominator, sd.denominator], dtype=np.int)
        new_den = np.lcm(dens[0], dens[1])
        a_mult = new_den // dens
        new_num = np.dot(a_mult, [self.numerator, sd.numerator])
        return FractionalSymbolicDuration(new_num, new_den)

    def __radd__(self, sd):

        return self.__add__(sd)

        # if isinstance(sd, int):
        #     sd = FractionalSymbolicDuration(sd, 1)

        # dens = np.array([self.denominator, sd.denominator], dtype=np.int)
        # new_den = np.lcm(dens[0], dens[1])
        # a_mult = new_den // dens
        # new_num = np.dot(a_mult, [self.numerator, sd.numerator])
        # return FractionalSymbolicDuration(new_num, new_den)


def pitch_name_2_midi_PC(modifier, name, octave):
    """
    To be replaced!
    """
    if name == 'r':
        return (0, 0)
    base_class = ({'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}[name.lower()] +
                  {'b': -1, 'bb': -2, '#': 1, 'x': 2, '##': 2, 'n': 0}[modifier])
    mid = (octave + 1) * 12 + base_class
    # for mozartmatch files (in which the octave numbers are off by one)
    # mid = octave*12 + base_class
    pitchclass = np.mod(base_class, 12)
    return (mid, pitchclass)


def interpret_field(data):
    """
    Convert data to int, if not possible, to float, otherwise return
    data itself.

    Parameters
    ----------
    data : object
       Some data object

    Returns
    -------
    data : int, float or same data type as the input
       Return the data object casted as an int, float or return
       data itself.
    """

    try:
        return int(data)
    except ValueError:
        try:
            return float(data)
        except ValueError:
            return data


class ParseRationalException(Exception):
    def __init__(self, string):
        self.string = string

    def __str__(self):
        return 'Could not parse string "{0}"'.format(self.string)


class Ratio:
    def __init__(self, string):
        try:
            self.numerator, self.denominator = [
                int(i) for i in string.split('/')]
        except:
            raise ParseRationalException(string)


def interpret_field_rational(data, allow_additions=True, rationals_as_list=True):
    """Convert data to int, if not possible, to float, if not possible
    try to interpret as rational number and return it as float, if not
    possible, return data itself."""
    # global rational_pattern
    v = interpret_field(data)
    if type(v) == str:
        m = rational_pattern.match(v)
        m2 = double_rational_pattern.match(v)
        if m:
            groups = m.groups()
            if rationals_as_list:
                return [int(g) for g in groups]
            else:
                return FractionalSymbolicDuration(*[int(g) for g in groups])
        elif m2:
            groups = m2.groups()
            if rationals_as_list:
                return [int(g) for g in groups]
            else:
                return FractionalSymbolicDuration(*[int(g) for g in groups])
        else:
            if allow_additions:
                parts = v.split('+')

                if len(parts) > 1:
                    iparts = [interpret_field_rational(
                        i, allow_additions=False, rationals_as_list=False) for i in parts]

                    # to be replaced with isinstance(i,numbers.Number)
                    if all(type(i) in (int, float, FractionalSymbolicDuration) for i in iparts):
                        if any([isinstance(i, FractionalSymbolicDuration) for i in iparts]):
                            iparts = [FractionalSymbolicDuration(i) if not isinstance(i, FractionalSymbolicDuration) else i
                                      for i in iparts]
                        return sum(iparts)
                    else:
                        return v
                else:
                    return v
            else:
                return v
    else:
        return v

###################################################


class MatchLine(object):

    out_pattern = ''
    field_names = []
    re_obj = re.compile('')
    field_interpreter = interpret_field_rational

    def __str__(self):
        r = [self.__class__.__name__]
        for fn in self.field_names:
            r.append(' {0}: {1}'.format(fn, self.__dict__[fn]))
        return '\n'.join(r) + '\n'

    @property
    def matchline(self):
        raise NotImplementedError

    @classmethod
    def match_pattern(cls, s, pos=0):
        return cls.re_obj.search(s, pos=pos)

    @classmethod
    def from_matchline(cls, matchline, pos=0):
        match_pattern = cls.re_obj.search(matchline, pos)

        if match_pattern is not None:

            groups = [cls.field_interpreter(i) for i in match_pattern.groups()]
            kwargs = dict(zip(cls.field_names, groups))

            match_line = cls(**kwargs)

            return match_line

        else:
            raise MatchError('Input match line does not fit the expected pattern.')


class MatchInfo(MatchLine):
    out_pattern = 'info({Attribute},{Value}).'
    field_names = ['Attribute', 'Value']
    pattern = 'info\(\s*([^,]+)\s*,\s*(.+)\s*\)\.'
    re_obj = re.compile(pattern)
    field_interpreter = interpret_field

    def __init__(self, Attribute, Value):
        self.Attribute = Attribute
        self.Value = Value

    @property
    def matchline(self):
        return self.out_pattern.format(
            Attribute=self.Attribute,
            Value=self.Value)


class MatchMeta(MatchLine):

    out_pattern = 'meta({Attribute},{Value},{Bar},{TimeInBeats}).'
    field_names = ['Attribute', 'Value', 'Bar', 'TimeInBeats']
    pattern = 'meta\(\s*([^,]*)\s*,\s*([^,]*)\s*,\s*([^,]*)\s*,\s*([^,]*)\s*\)\.'
    re_obj = re.compile(pattern)
    field_interpreter = interpret_field

    def __init__(self, Attribute, Value, Bar, TimeInBeats):
        self.Attribute = Attribute
        self.Value = Value
        self.Bar = Bar
        self.TimeInBeats = TimeInBeats

    @property
    def matchline(self):
        return self.out_pattern.format(
            Attribute=self.Attribute,
            Value=self.Value,
            Bar=self.Bar,
            TimeInBeats=self.TimeInBeats)


class MatchSnote(MatchLine):
    """
    Class representing a score note
    """

    out_pattern = ('snote({Anchor},[{NoteName},{Modifier}],{Octave},'
                   + '{Bar}:{Beat},{Offset},{Duration},'
               + '{OnsetInBeats},{OffsetInBeats},'
                   + '[{ScoreAttributesList}])')

    pattern = 'snote\(([^,]+),\[([^,]+),([^,]+)\],([^,]+),([^,]+):([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),\[(.*)\]\)'
    re_obj = re.compile(pattern)

    field_names = ['Anchor', 'NoteName', 'Modifier', 'Octave',
                   'Bar', 'Beat', 'Offset', 'Duration',
                   'OnsetInBeats', 'OffsetInBeats', 'ScoreAttributesList']

    def __init__(self, Anchor, NoteName, Modifier, Octave, Bar, Beat,
                 Offset, Duration, OnsetInBeats, OffsetInBeats,
                 ScoreAttributesList=[]):

        self.Anchor = Anchor
        self.NoteName = NoteName
        self.Modifier = Modifier
        self.Octave = Octave
        self.Bar = Bar
        self.Beat = Beat

        if isinstance(Offset, int):
            self.Offset = FractionalSymbolicDuration(Offset, 1)
        elif isinstance(Offset, (list, tuple)):
            self.Offset = FractionalSymbolicDuration(*Offset)
        elif isinstance(Offset, FractionalSymbolicDuration):
            self.Offset = Offset

        if isinstance(Duration, int):
            self.Duration = FractionalSymbolicDuration(Duration, 1)
        elif isinstance(Duration, (list, tuple)):
            self.Duration = FractionalSymbolicDuration(*Duration)
        elif isinstance(Duration, FractionalSymbolicDuration):
            self.Duration = Duration

        # else:
        #     try:
        #         self.Duration = FractionalSymbolicDuration(*Duration)
        #     except:
        #         print(Duration)
        #         import pdb
        #         pdb.set_trace()
            # raise ValueError('Invalid Duration')

        # self.Duration = Duration
        self.OnsetInBeats = OnsetInBeats
        self.OffsetInBeats = OffsetInBeats

        if isinstance(ScoreAttributesList, (list, tuple, np.ndarray)):
            # Always cast ScoreAttributesList as list?
            self.ScoreAttributesList = list(ScoreAttributesList)
        elif isinstance(ScoreAttributesList, str):
            self.ScoreAttributesList = ScoreAttributesList.split(',')
        elif isinstance(ScoreAttributesList, (int, float)):
            self.ScoreAttributesList = [ScoreAttributesList]
        else:

            print(ScoreAttributesList)
            import pdb
            pdb.set_trace()
            raise ValueError('`ScoreAttributesList` must be a list or a string')

    @property
    def DurationInBeats(self):
        return self.OffsetInBeats - self.OnsetInBeats

    @property
    def DurationSymbolic(self):
        if isinstance(self.Duration, FractionalSymbolicDuration):
            return str(self.Duration)
        elif isinstance(self.Duration, (float, int)):
            return str(Fraction.from_float(self.Duration))
        elif isinstance(self.Duration, str):
            return self.Duration

    @property
    def MidiPitch(self):
        if isinstance(self.Octave, int):
            return pitch_name_2_midi_PC(self.Modifier, self.NoteName, self.Octave)
        else:
            return None

    @property
    def matchline(self):
        return self.out_pattern.format(
            Anchor=self.Anchor,
            NoteName=self.NoteName,
            Modifier=self.Modifier,
            Octave=self.Octave,
            Bar=self.Bar,
            Beat=self.Beat,
            # Offset=str(Fraction.from_float(self.Offset)),
            Offset=str(self.Offset),
            Duration=self.DurationSymbolic,
            OnsetInBeats=self.OnsetInBeats,
            OffsetInBeats=self.OffsetInBeats,
            ScoreAttributesList=','.join(self.ScoreAttributesList))


class MatchNote(MatchLine):
    """
    Class representing the performed note part of a match line
    """
    out_pattern = ('note({Number},[{NoteName},{Modifier}],' +
                   '{Octave},{Onset},{Offset},{AdjOffset},{Velocity})')

    field_names = ['Number', 'NoteName', 'Modifier', 'Octave',
                   'Onset', 'Offset', 'AdjOffset', 'Velocity']
    pattern = 'note\(([^,]+),\[([^,]+),([^,]+)\],([^,]+),([^,]+),([^,]+),([^,]+),([^,]+)\)'

    re_obj = re.compile(pattern)

    # For backwards compatibility with Matchfile Version 1
    field_names_v1 = ['Number', 'NoteName', 'Modifier', 'Octave',
                      'Onset', 'Offset', 'Velocity']
    pattern_v1 = 'note\(([^,]+),\[([^,]+),([^,]+)\],([^,]+),([^,]+),([^,]+),([^,]+)\)'
    re_obj_v1 = re.compile(pattern_v1)

    def __init__(self, Number, NoteName, Modifier,
                 Octave, Onset, Offset, AdjOffset,
                 Velocity, MidiPitch=None, version=LATEST_VERSION):

        self.Number = Number

        # check if all pitch spelling information was provided
        has_pitch_spelling = not (
            NoteName is None or Modifier is None or Octave is None)

        # check if the MIDI pitch of the note was provided
        has_midi_pitch = MidiPitch is not None

        # Raise an error if neither pitch spelling nor MIDI pitch were provided
        if not has_pitch_spelling and not has_midi_pitch:
            raise ValueError('No note height information provided!')

        # Set attributes regarding pitch spelling
        if has_pitch_spelling:
            # Ensure that note name is uppercase
            if NoteName.upper() in NOTE_NAMES:
                self.NoteName = NoteName.upper()
            else:
                raise ValueError(
                    'Invalid note name. Should be in {0}'.format(','.join(NOTE_NAMES)))

            self.Modifier = Modifier
            self.Octave = int(Octave)

        else:
            # infer the pitch information from the MIDI pitch
            # Note that this is just a dummy method, and does not correspond to
            # musically correct pitch spelling.
            self.NoteName, self.Modifier = PC_DICT[int(np.mod(MidiPitch, 12))]
            self.Octave = int(MidiPitch // 12 - 1)

        # Check if the provided MIDI pitch corresponds to the correct pitch spelling
        if has_midi_pitch:
            if MidiPitch != pitch_name_2_midi_PC(self.Modifier,
                                                 self.NoteName,
                                                 self.Octave)[0]:
                raise ValueError('The provided pitch spelling information does not match '
                                 'the given MIDI pitch!')

            else:
                # Set the Midi pitch
                self.MidiPitch = (int(MidiPitch), int(np.mod(MidiPitch, 12)))

        self.Onset = Onset
        self.Offset = Offset
        self.AdjOffset = AdjOffset

        if AdjOffset is None:
            # Raise warning!
            self.AdjOffset = self.Offset

        self.Velocity = int(Velocity)

        # TODO
        # * check version and update necessary patterns
        self.version = version

    @property
    def matchline(self):
        return self.out_pattern.format(
            Number=self.Number,
            NoteName=self.NoteName,
            Modifier=self.Modifier,
            Octave=self.Octave,
            Onset=self.Onset,
            Offset=self.Offset,
            AdjOffset=self.AdjOffset,
            Velocity=self.Velocity)

    @property
    def Duration(self):
        return self.Offset - self.Onset

    def AdjDuration(self):
        return self.AdjOffset - self.Onset

    @classmethod
    def from_matchline(cls, matchline, pos=0):
        """Create a MatchNote from a line

        """
        match_pattern = cls.re_obj.search(matchline, pos)

        if match_pattern is None:
            match_pattern = cls.re_obj_v1.search(matchline, pos)

            if match_pattern is not None:
                groups = [cls.field_interpreter(i) for i in match_pattern.groups()]
                kwargs = dict(zip(cls.field_names_v1, groups))
                kwargs['version'] = 1.0
                kwargs['AdjOffset'] = None
                match_line = cls(**kwargs)

                return match_line
            else:
                raise MatchError('Input matchline does not fit expected pattern')

        else:
            groups = [cls.field_interpreter(i) for i in match_pattern.groups()]
            kwargs = dict(zip(cls.field_names, groups))
            match_line = cls(**kwargs)
            return match_line


class MatchSnoteNote(MatchLine):
    """
    Class representing a "match" (containing snote and note)

    TODO:
    * More readable __str__ method

    """

    out_pattern = '{SnoteLine}-{NoteLine}.'
    pattern = MatchSnote.pattern + '-' + MatchNote.pattern
    re_obj = re.compile(pattern)
    field_names = MatchSnote.field_names + MatchNote.field_names

    # for version 1
    pattern_v1 = MatchNote.pattern + '-' + MatchNote.pattern_v1
    re_obj_v1 = re.compile(pattern_v1)
    field_names_v1 = MatchSnote.field_names + MatchNote.field_names_v1

    def __init__(self, snote, note, same_pitch_spelling=True):
        self.snote = snote
        self.note = note

        # Set the same pitch spelling in both note and snote
        # (this can break if the snote is not exactly matched
        # to a note with the same pitch). Handle with care.
        if same_pitch_spelling:
            self.note.NoteName = self.snote.NoteName
            self.note.Modifier = self.snote.Modifier
            self.note.Octave = self.snote.Octave

    @property
    def matchline(self):
        return self.out_pattern.format(
            SnoteLine=self.snote.matchline,
            NoteLine=self.note.matchline)

    @classmethod
    def from_matchline(cls, matchline, pos=0):
        match_pattern = cls.re_obj.search(matchline, pos=0)

        if match_pattern is None:
            match_pattern = cls.re_obj_v1.search(matchline, pos)

            if match_pattern is not None:
                groups = [cls.field_interpreter(i) for i in match_pattern.groups()]

                snote_kwargs = dict(zip(MatchSnote.field_names,
                                        groups[:len(MatchSnote.field_names)]))
                note_kwargs = dict(zip(MatchNote.field_names_v1,
                                       groups[len(MatchSnote.field_names):]))
                note_kwargs['version'] = 1.0
                note_kwargs['AdjOffset'] = None
                snote = MatchSnote(**snote_kwargs)
                note = MatchNote(**note_kwargs)
                match_line = cls(snote=snote,
                                 note=note)

                return match_line
            else:
                raise MatchError('Input matchline does not fit expected pattern')

        else:
            groups = [cls.field_interpreter(i) for i in match_pattern.groups()]
            snote_kwargs = dict(zip(MatchSnote.field_names,
                                    groups[:len(MatchSnote.field_names)]))
            note_kwargs = dict(zip(MatchNote.field_names,
                                   groups[len(MatchSnote.field_names):]))
            snote = MatchSnote(**snote_kwargs)
            note = MatchNote(**note_kwargs)
            match_line = cls(snote=snote,
                             note=note)
            return match_line

    def __str__(self):
        # TODO:
        # Nicer print?
        return str(self.snote) + '\n' + str(self.note)


class MatchSnoteDeletion(MatchLine):
    out_pattern = '{SnoteLine}-deletion.'
    pattern = MatchSnote.pattern + '-deletion\.'
    re_obj = re.compile(pattern)
    field_names = MatchSnote.field_names

    def __init__(self, snote):
        self.snote = snote

    @property
    def matchline(self):
        return self.out_pattern.format(
            SnoteLine=self.snote.matchline)

    @classmethod
    def from_matchline(cls, matchline, pos=0):
        match_pattern = cls.re_obj.search(matchline, pos=0)

        if match_pattern is not None:
            groups = [cls.field_interpreter(i) for i in match_pattern.groups()]
            snote_kwargs = dict(zip(MatchSnote.field_names, groups))
            try:
                snote = MatchSnote(**snote_kwargs)
            except:
                import pdb
                pdb.set_trace()
            match_line = cls(snote=snote)
            return match_line

        else:
            raise MatchError('Input matchline does not fit expected pattern')

    def __str__(self):
        return str(self.snote) + '\nDeletion'


class MatchInsertionNote(MatchLine):
    out_pattern = 'insertion-{NoteLine}.'
    pattern = 'insertion-' + MatchNote.pattern + '.'
    re_obj = re.compile(pattern)
    field_names = MatchNote.field_names

    def __init__(self, note):
        self.note = note
        for fn in self.field_names:
            setattr(self, fn, getattr(self.note, fn, None))

    @property
    def matchline(self):
        return self.out_pattern.format(
            NoteLine=self.note.matchline)

    @classmethod
    def from_matchline(cls, matchline, pos=0):
        match_pattern = cls.match_pattern(matchline, pos=0)

        if match_pattern is not None:
            groups = [cls.field_interpreter(i) for i in match_pattern.groups()]
            note_kwargs = dict(zip(MatchNote.field_names, groups))
            note = MatchNote(**note_kwargs)
            return cls(note=note)
        else:
            raise MatchError('Input matchline does not fit expected pattern')


class MatchSustainPedal(MatchLine):
    """
    Class for representing a sustain pedal line
    """
    out_pattern = 'sustain({Time},{Value}).'
    field_names = ['Time', 'Value']
    pattern = 'sustain\(\s*([^,]*)\s*,\s*([^,]*)\s*\)\.'
    re_obj = re.compile(pattern)

    def __init__(self, Time, Value):
        self.Time = Time
        self.Value = Value

    @property
    def matchline(self):

        return self.out_pattern.format(
            Time=self.Time,
            Value=self.Value)


class MatchSoftPedal(MatchLine):
    """
    Class for representing a soft pedal line
    """
    out_pattern = 'soft({Time},{Value}).'
    field_names = ['Time', 'Value']
    pattern = 'soft\(\s*([^,]*)\s*,\s*([^,]*)\s*\)\.'
    re_obj = re.compile(pattern)

    def __init__(self, Time, Value):
        self.Time = Time
        self.Value = Value

    @property
    def matchline(self):

        return self.out_pattern.format(
            Time=self.Time,
            Value=self.Value)


class MatchOrnamentNote(MatchLine):
    out_pattern = 'ornament({Anchor})-{NoteLine}'
    field_names = ['Anchor'] + MatchNote.field_names
    pattern = 'ornament\([^\)]*\)-' + MatchNote.pattern
    re_obj = re.compile(pattern)

    def __init__(self, anchor, note):
        self.Anchor = anchor
        self.note = note

    @property
    def matchline(self):
        return self.out_pattern.format(
            Anchor=self.Anchor,
            NoteLine=self.note.matchline)

    @classmethod
    def from_matchline(cls, matchline, pos=0):
        match_pattern = cls.match_pattern(matchline, pos=0)

        if match_pattern is not None:
            groups = [cls.field_interpreter(i) for i in match_pattern.groups()]
            note_kwargs = groups[1:]
            anchor = groups[0]
            note = MatchNote(**note_kwargs)
            return cls(Anchor=anchor,
                       note=note)

        else:
            raise MatchError('Input matchline does not fit expected pattern')


def parse_matchline(l):
    """
    Return objects representing the line as one of:

    * hammer_bounce-PlayedNote.
    * info(Attribute, Value).
    * insertion-PlayedNote.
    * ornament(Anchor)-PlayedNote.
    * ScoreNote-deletion.
    * ScoreNote-PlayedNote.
    * ScoreNote-trailing_score_note.
    * trailing_played_note-PlayedNote.
    * trill(Anchor)-PlayedNote.
    * meta(Attribute, Value, Bar, Beat).

    or False if none can be matched

    Parameters
    ----------
    l : str
        Line of the match file

    Returns
    -------
    matchline : subclass of `MatchLine`
       Object representing the line.
    """

    from_matchline_methods = [MatchSnoteNote.from_matchline,
                              MatchSnoteDeletion.from_matchline,
                              MatchInsertionNote.from_matchline,
                              MatchSustainPedal.from_matchline,
                              MatchSoftPedal.from_matchline,
                              MatchInfo.from_matchline,
                              MatchMeta.from_matchline
                              ]
    matchline = False
    for from_matchline in from_matchline_methods:
        try:
            matchline = from_matchline(l)
            break
        except MatchError:
            continue

    return matchline


class MatchFile(object):
    """
    Class for representing MatchFiles
    """

    def __init__(self, filename, pedal_threshold=64):

        fileData = [l.decode('utf8').strip() for l in open(filename, 'rb')]

        self.name = filename

        self.lines = np.array([parse_matchline(l) for l in fileData])

        self.pedal_threshold = 64

    @property
    def note_pairs(self):
        """
        Return all(snote, note) tuples

        """
        return [(x.snote, x.note) for x in self.lines if isinstance(x, SnoteNoteLine)]

    @property
    def notes(self):
        """
        Return all performed notes (as MatchNote objects)
        """
        return [x.note for x in self.lines if hasattr(x, 'note')]

    @property
    def snotes(self):
        """
        Return all score notes (as MatchSnote objects)
        """
        return [x.snote for x in self.lines if hasattr(x, 'snote')]

    @property
    def pedal_threshold(self):
        return self._pedal_threshold

    @pedal_threshold.setter
    def pedal_threshold(self, value):
        self._pedal_threshold = value
        # adjust sound off (AdjOffset) here...

    @property
    def _info(self):
        """
        Return all InfoLine objects

        """
        return [i for i in self.lines if isinstance(i, MatchInfo)]

    def info(self, attribute=None):
        """
        Return the value of the MatchInfo object corresponding to
        attribute, or None if there is no such object

        : param attribute: the name of the attribute to return the value for

        """
        if attribute:
            try:
                idx = [i.Attribute for i in self._info].index(attribute)
                return self._info[idx].Value
            except:
                return None
        else:
            return self._info

    @property
    def first_onset(self):
        return min([n.OnsetInBeats for n in self.snotes])

    @property
    def time_signatures(self):
        """
        A list of tuples(t, (a, b)), indicating a time signature of a over b, starting at t

        """
        tspat = re.compile('([0-9]+)/([0-9]*)')
        m = [(int(x[0]), int(x[1])) for x in
             tspat.findall(self.info('timeSignature'))]
        _timeSigs = []
        if len(m) > 0:
            _timeSigs.append((self.first_onset, m[0]))
        for l in self.time_sig_lines:
            _timeSigs.append((float(l.TimeInBeats), [
                            (int(x[0]), int(x[1])) for x in tspat.findall(l.Value)][0]))
        _timeSigs = list(set(_timeSigs))
        _timeSigs.sort(key=lambda x: x[0])

        # ensure that all consecutive time signatures are different
        timeSigs = [_timeSigs[0]]

        for ts in _timeSigs:
            ts_on, (ts_num, ts_den) = ts
            ts_on_prev, (ts_num_prev, ts_den_prev) = timeSigs[-1]
            if ts_num != ts_num_prev or ts_den != ts_den_prev:
                timeSigs.append(ts)

        return timeSigs

    def _time_sig_lines(self):
        return [i for i in self.lines if
                isinstance(i, MatchMeta)
                and hasattr(i, 'Attribute')
                and i.Attribute == 'timeSignature']

    @property
    def time_sig_lines(self):
        ml = self._time_sig_lines()
        if len(ml) == 0:
            ts = self.info('timeSignature')
            ml = [parse_matchline(
                'meta(timeSignature,{0},1,{1}).'.format(ts, self.first_onset))]
        return ml
