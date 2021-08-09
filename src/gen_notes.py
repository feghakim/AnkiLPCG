from itertools import zip_longest
import re
import math
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, TYPE_CHECKING
from enum import Enum, auto
import sys
import json

if TYPE_CHECKING:
    from anki.notes import Note

TESTING = True
if 'pytest' not in sys.modules:
    TESTING = False
    from aqt import mw


class PoemLine:
    def __init__(self) -> None:
        self.predecessor = self  # so it's the right type...
        self.successor: Optional['PoemLine'] = None
        self.seq = -1
        self.start_index = -1
        self.subtitle = ''

    def populate_note(self, note: 'Note', title: str, tags: List[str],
                      context_lines: int, recite_lines: int, deck_id: int,
                      step: int = 1, media: List[str] = []) -> None:
        """
        Fill the _note_ with content testing on the current line.
        """
        note.model()['did'] = deck_id  # type: ignore
        note.tags = tags
        note['العنوان'] = title
        note['الباب'] = self._format_subtitles(context_lines)
        note['الرقم'] = str(math.ceil(self.seq/step))
        note['السياق'] = self._format_context(context_lines)
        note['الأبيات'] = self._format_text(recite_lines)
        note['وسائط'] = self._format_media(media)
        note['الحالي'] = str(self.start_index)
        note['خاص (لا تعدل)'] = f'<img src="_{title}.js">'
        prompt = self._get_prompt(recite_lines)
        if prompt is not None:
            note['محث'] = prompt

    def _format_media(self, media: List[str] = []):
        return ''.join(name for name in media)

    def _format_subtitles(self, context_lines: int):
        if self.subtitle:
            subs = [f"<p>{self.subtitle}</p>"]
        else:
            subs = []
        cur = self.predecessor
        suc = self
        while context_lines > 0:
            if cur.subtitle and cur.subtitle != suc.subtitle:
                subs.append(f"<p>{cur.subtitle}</p>")
            suc = cur
            cur = cur.predecessor
            context_lines-= 1
        return ''.join(reversed(subs))

    def _format_context(self, context_lines: int):
        return ''.join("<p>%s</p>" % i for i in self._get_context(context_lines))

    def _format_text(self, recitation_lines: int):
        return ''.join("<p>%s</p>" % i for i in self._get_text(recitation_lines))

    def _get_context(self, _lines: int, _recursing=False) -> List[str]:
        """
        Return a list of context lines, including the current line and
        (lines - 1) of its predecessors.
        """
        raise NotImplementedError

    def _get_text(self, _lines: int) -> List[str]:
        """
        Return a list of recitation lines, including the current line and
        (lines - 1) of its successors.
        """
        raise NotImplementedError

    def _get_prompt(self, configured_recitation_lines: int) -> Optional[str]:
        """
        Return a prompt string to be shown on the question side after the
        lines of context, or None to use the template default of [...]. This
        is currently used to let the user know how many lines to recite, but
        could plausibly be used for other things as well in the future.
        """
        raise NotImplementedError


class Beginning(PoemLine):
    """
    A dummy node indicating the beginning of the poem. It's included only so
    it can polymorphically have its context and sequence retrieved.
    Attempting to do anything else with the node is an error.
    """
    def __init__(self, text):
        super().__init__()
        self.seq = 0
        self.start_index = 0
        self.text = text

    def _get_context(self, _lines: int, _recursing=False) -> List[str]:
        return [self.text]

    def _get_text(self, _lines: int) -> List[str]:
        """
        The Beginning node has no defined successors, as it's not a line
        we'll ever be asked to recite and thus we never need to know what its
        text property is -- the first line we would ever be asked to recite
        would be the following line.
        """
        raise NotImplementedError

    def populate_note(self, note: 'Note', title: str, tags: List[str],
                      context_lines: int, recite_lines: int, deck_id: int,
                      step: int = 1, media: List[str] = []) -> None:
        raise AssertionError("The Beginning node cannot be used to populate a note.")


class SingleLine(PoemLine):
    """
    A single line in a typical poem. It has text, a sequence number, a
    predecessor (possibly the Beginning node, but never None), and if it's
    not the last line of the poem, a successor.
    """
    def __init__(self, text: str, predecessor: 'PoemLine', subtitle: str = '') -> None:
        super().__init__()
        self.text = text
        self.predecessor = predecessor
        self.seq = self.predecessor.seq + 1
        self.start_index = self.predecessor.start_index + 1
        self.subtitle = subtitle

    def _get_context(self, lines: int, recursing=False) -> List[str]:
        if lines == 0:
            return [self.text]
        elif not recursing:
            return self.predecessor._get_context(lines - 1, True)
        else:
            return self.predecessor._get_context(lines - 1, True) + [self.text]

    def _get_text(self, lines: int) -> List[str]:
        if lines == 1 or self.successor is None:
            return [self.text]
        else:
            return [self.text] + self.successor._get_text(lines - 1)

    def _get_prompt(self, configured_recitation_lines: int) -> Optional[str]:
        # It's important to calculate the lines_to_recite for _this_ instance
        # instead of just getting the configuration parameter, as if we're at
        # the end it may be fewer.
        lines_to_recite = len(self._get_text(configured_recitation_lines))
        if lines_to_recite == 1:
            return None
        else:
            return f"[...{lines_to_recite}]"


class GroupedLine(PoemLine):
    r"""
    A virtual "line" in a poem that has grouping set, so that multiple short
    lines can be treated as one line by LPCG. It consists of multiple text lines.

    The difference between grouped lines and ordinary lines with double the
    context and recitation values is that there is no overlapping. So this with
    default context and recitation values and a group of 2 yields only 3 notes,
    whereas a context of 4 and recitation of 2 would result in 6 notes:

        /A
        \B
        /C
        \D
        /E
        \F
    """
    def __init__(self, text: List[str], predecessor: 'PoemLine', subtitle = '') -> None:
        super().__init__()
        self.text_lines = text
        self.predecessor = predecessor
        self.seq = self.predecessor.seq + 1
        self.start_index = self.predecessor.start_index + len(getattr(self.predecessor, 'text_lines', ['']))
        self.subtitle = subtitle

    def _get_context(self, lines: int, recursing=False) -> List[str]:
        if lines == 0:
            return self.text_lines
        elif not recursing:
            return self.predecessor._get_context(lines - 1, True)
        else:
            return self.predecessor._get_context(lines - 1, True) + self.text_lines

    def _get_text(self, lines: int) -> List[str]:
        if lines == 1 or self.successor is None:
            return self.text_lines
        else:
            return self.text_lines + self.successor._get_text(lines - 1)

    def _get_prompt(self, configured_recitation_lines: int) -> Optional[str]:
        lines_to_recite = len(self._get_text(configured_recitation_lines))
        if lines_to_recite == 1:
            return None
        else:
            return f"[...{lines_to_recite}]"

    def _format_subtitles(self, context_lines: int):
        if context_lines < 0:
            return ''
        subs = []
        if isinstance(self.subtitle, str):
            subs.append(f"<p>{self.subtitle}</p>")
        elif isinstance(self.subtitle, Iterable):
            prev = ''
            for s in self.subtitle:
                if s and s != prev:
                    subs.append(f"<p>{s}</p>")
                prev = s
        else:
            return ''
        prev_sub = self.predecessor._format_subtitles(context_lines-1)
        sub = ''.join(reversed(subs))
        return prev_sub + sub


class PoemSection(GroupedLine):
    """
    A poem section having a number of lines, subtitle, and no context lines.

    Intended to be used when the user wants each note to contain a whole section.

    The subtitle is stored in the context field though; this is done because
    some people found it more aesthetic.
    """
    def _get_text(self, lines: int) -> List[str]:
         return self.text_lines

    def _get_context(self, lines: int, recursing=False) -> List[str]:
        return [self.subtitle]

    def _format_subtitles(self, context_lines: int):
        return ''


def groups_of_n(iterable: Iterable, n: int) -> Iterable:
    """
    s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ...

    Credit: https://stackoverflow.com/questions/5389507/iterating-over-every-two-elements-in-a-list
    """
    return zip_longest(*[iter(iterable)]*n)


def save_whole_poem(poemlines, title) -> None:
    current = 1
    def format_line(text):
        nonlocal current
        s = f'<p id="arlpcg-text-{current}">{text}</p>'
        current += 1
        return s

    lines = []
    def add_line(poemline):
        if hasattr(poemline, 'text'):
            lines.append(format_line(poemline.text))
        else:
            lines.extend(map(lambda l: format_line(l), poemline.text_lines))

    for poemline in poemlines:
        add_line(poemline)

    # save whole poem to media folder
    if not TESTING:
        poem = ''.join(lines)
        js = f"var ARLPCGText = {json.dumps(poem, ensure_ascii=False)};"
        fname = f"_{title}.js"
        mw.col.media.trash_files([fname])
        mw.col.media.write_data(fname, js.encode())


def _poemlines_from_textlines(config: Dict[str, Any], text_lines: List[str], group_lines: int) -> List[PoemLine]:
    """
    Given a list of cleansed text lines, create a list of PoemLine objects
    from it. These are each capable of constructing a correct note testing
    themselves when the to_note() method is called on them.
    """
    beginning = Beginning(config.get("beginningLine", "[البداية]"))
    lines: List[PoemLine] = []  # does not include beginning, as it's not actually a line
    pred: PoemLine = beginning
    poem_line: PoemLine

    if group_lines == 1:
        for text_line in text_lines:
            poem_line = SingleLine(text_line, pred)
            lines.append(poem_line)
            pred.successor = poem_line
            pred = poem_line
    else:
        for line_set in groups_of_n(text_lines, group_lines):
            poem_line = GroupedLine([i for i in line_set if i is not None], pred)
            lines.append(poem_line)
            pred.successor = poem_line
            pred = poem_line
    return lines


def _poemlines_from_textlines_automatic(config: Dict[str, Any], text_lines: Dict, group_lines: int) -> List[PoemLine]:

    beginning = Beginning(config.get("beginningLine", "[البداية]"))
    lines: List[PoemLine] = []
    pred: PoemLine = beginning
    poem_line: PoemLine

    if group_lines == 1:
        for i, text_line in enumerate(text_lines["verses"]):
            poem_line = SingleLine(text_line, pred, text_lines["subtitles"][i])
            lines.append(poem_line)
            pred.successor = poem_line
            pred = poem_line
    else:
        subtitle_set = list(groups_of_n(text_lines["subtitles"], group_lines))
        for i, line_set in enumerate(groups_of_n(text_lines["verses"], group_lines)):
            poem_line = GroupedLine([i for i in line_set if i is not None], pred, subtitle_set[i])
            lines.append(poem_line)
            pred.successor = poem_line
            pred = poem_line
    return lines


def _poemlines_from_textlines_by_section(config: Dict[str, Any], text_lines: Dict) -> List[Tuple[int, PoemLine]]:

    beginning = Beginning(config.get("beginningLine", "[البداية]"))
    lines: List[Tuple[int, PoemLine]] = []
    pred: PoemLine = beginning
    poem_line: PoemLine

    def get_section_lines():
        cur_subtitle = text_lines["subtitles"][0]
        section_lines_count = 0
        for i in range(len(text_lines["verses"])):
            if cur_subtitle != text_lines["subtitles"][i]:
                yield (cur_subtitle, text_lines["verses"][i-section_lines_count:i])
                cur_subtitle = text_lines["subtitles"][i]
                section_lines_count = 0
            section_lines_count += 1
        yield (cur_subtitle, text_lines["verses"][i-section_lines_count+1:])

    for subtitle, section_lines in get_section_lines():
        poem_line = PoemSection(section_lines, pred, subtitle)
        lines.append((len(section_lines), poem_line))
        pred.successor = poem_line
        pred = poem_line
    return lines


def cleanse_text(string: str, config: Dict[str, Any]) -> List[str]:
    """
    Munge raw text from the poem editor into a list of lines that can be
    directly made into notes.
    """
    def _normalize_blank_lines(text_lines):
        # remove consecutive lone newlines
        new_text = []
        last_line = ""
        for i in text_lines:
            if last_line.strip() or i.strip():
                new_text.append(i)
            last_line = i
        # remove lone newlines at beginning and end
        for i in (0, -1):
            if not new_text[i].strip():
                del new_text[i]
        return new_text

    text = string.splitlines()
    # record a level of indentation if appropriate
    text = [re.sub(r'^[ \t]+', r'<indent>', i) for i in text]
    # remove comments and normalize blank lines
    text = [i.strip() for i in text if not i.startswith("#")]
    text = [re.sub(r'\s*\#.*$', '', i) for i in text]

    text = _normalize_blank_lines(text)
    # add end-of-stanza/poem markers where appropriate
    for i in range(len(text)):
        if i == len(text) - 1:
            text[i] += config['endOfTextMarker']
        elif not text[i+1].strip():
            text[i] += config['endOfStanzaMarker']
    # entirely remove all blank lines
    text = [i for i in text if i.strip()]
    # replace <indent>s with valid CSS
    text = [re.sub(r'^<indent>(.*)$', r'<span class="indent">\1</span>', i)
            for i in text]
    return text


def automatic_parse_text(lines: List[str], caesura: str) -> Dict:
    ret: Dict = {}
    #FIXME: maybe use the typed title if there is no one in the poem text?
    ret['title'] = lines[0]
    i = 1

    ret['verses'] = []
    ret['subtitles'] = []
    cur_subtitle = ''
    while i < len(lines):
        if caesura not in lines[i]:
            cur_subtitle = lines[i]
        else:
            ret['verses'].append(lines[i])
            ret['subtitles'].append(cur_subtitle)
        i += 1
    return ret


class ImportMode(Enum):
    CUSTOM = auto()
    AUTOMATIC = auto()
    BY_SECTION = auto()

class MediaImportMode(Enum):
    BULK = auto()
    ONE_FOR_EACH_NOTE = auto()
    BY_RECITE_LINES = auto()


def add_notes(col: Any, config: Dict[str, Any], note_constructor: Callable,
              title: str, tags: List[str], text: List[str], deck_id: int,
              context_lines: int, group_lines: int, recite_lines: int, step: int = 1,
              media: List[str] = [], media_mode: MediaImportMode = MediaImportMode.BULK,
              mode: ImportMode = ImportMode.CUSTOM, caesura: str = ' '):
    """
    Generate notes from the given title, tags, poem text, and number of
    lines of context. Return the number of notes added.

    Return the number of notes added.

    Raises KeyError if the note type is missing fields, which I've seen
    happen a couple times when users accidentally edited the note type. The
    caller should offer an appropriate error message in this case.
    """

    def choose_media(i: int, recite_lines: int, step: int = 1) -> List[str]:

        if media_mode == MediaImportMode.BULK:
            return media
        elif media_mode == MediaImportMode.ONE_FOR_EACH_NOTE:
            if mode == ImportMode.BY_SECTION:
                return media[i:i+1]
            else:
                return media[i*step:i*step+1]
        elif media_mode == MediaImportMode.BY_RECITE_LINES:
            if mode == ImportMode.BY_SECTION:
                return media[i:i+recite_lines]
            else:
                return media[i*step:i*step+recite_lines]
        else:
            raise Exception("unhandled media import mode")

    added = 0
    model = col.models.byName("ARLPCG 1.0")
    if mode == ImportMode.CUSTOM:
        lines = _poemlines_from_textlines(config, text, group_lines)[0::step]
        for line in lines:
            n = note_constructor(col, model)
            line.populate_note(n, title, tags, context_lines, recite_lines, deck_id, step, choose_media(added, recite_lines, step))
            col.addNote(n)
            added += 1
    elif mode == ImportMode.AUTOMATIC:
        parsed = automatic_parse_text(text, caesura)
        title = parsed['title']
        lines = _poemlines_from_textlines_automatic(config, parsed, group_lines)[0::step]
        for line in lines:
            n = note_constructor(col, model)
            line.populate_note(n, title, tags, context_lines, recite_lines, deck_id, step, choose_media(added, recite_lines, step))
            col.addNote(n)
            added += 1
    elif mode == ImportMode.BY_SECTION:
        parsed = automatic_parse_text(text, caesura)
        title = parsed['title']
        media_added = 0
        lines = _poemlines_from_textlines_by_section(config, parsed)
        for section_lines, line in lines:
            n = note_constructor(col, model)
            note_media = choose_media(media_added, section_lines)
            media_added += len(note_media)
            line.populate_note(n, title, tags, 0, section_lines, deck_id, 1, note_media)
            col.addNote(n)
            added += 1
        lines = map(lambda l: l[1], lines)

    save_whole_poem(lines, title)

    return added
