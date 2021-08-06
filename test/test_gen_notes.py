from textwrap import dedent
from typing import Sequence

import pytest

# pylint: disable=unused-wildcard-import
from src.gen_notes import *


MOCK_CLEANSE_CONFIG = {'endOfTextMarker': 'X', 'endOfStanzaMarker': 'Y'}
INDENT_HTML_START = '<span class="indent">'
INDENT_HTML_END = '</span>'


@pytest.mark.parametrize("n,expected", [
    (2, ((1, 2), (3, 4), (5, 6))),
    (3, ((1, 2, 3), (4, 5, 6))),
    (4, ((1, 2, 3, 4), (5, 6, None, None))),
])
def test_groups_of_n(n: int, expected: Sequence[int]):
    original_iterable = (1, 2, 3, 4, 5, 6)
    grouped = groups_of_n(original_iterable, n)
    for actual, exp in zip(grouped, expected):
        assert actual == exp


class TestCleanseText:
    def test_cleanse(self):
        limerick = dedent("""
        # Ulrich Neisser
        You can get a good deal from rehearsal
        If it just has the proper dispersal.   

          You would just be an ass
          To do it en masse,
        Your remembering would turn out much worsal.
        """).strip()
        result = cleanse_text(limerick, MOCK_CLEANSE_CONFIG)

        assert result[0] == "You can get a good deal from rehearsal"
        assert result[1] == "If it just has the proper dispersal.Y"
        assert result[2] == f"{INDENT_HTML_START}You would just be an ass{INDENT_HTML_END}"
        assert result[3] == f"{INDENT_HTML_START}To do it en masse,{INDENT_HTML_END}"
        assert result[4] == "Your remembering would turn out much worsal.X"


    def test_cleanse_multiple_blank_lines(self):
        test_case = dedent("""
        # This has lots of blank lines and comments that could mess things up.
        Here is a first line


        And here is a second line.
        And a third line.
        # Now a comment

        # And another comment

        And here, at last, is the end of the poem.
        """).strip() + "\n\n"
        result = cleanse_text(test_case, MOCK_CLEANSE_CONFIG)

        assert result[0] == "Here is a first lineY"
        assert result[1] == "And here is a second line."
        assert result[2] == "And a third line.Y"
        assert result[3] == "And here, at last, is the end of the poem.X"


    def test_unequal_indentation(self):
        limerick = dedent("""
        # Ulrich Neisser
        You can get a good deal from rehearsal
        If it just has the proper dispersal.   

        	You would just be an ass
           To do it en masse,
        Your remembering would turn out much worsal.
        """).strip()
        result = cleanse_text(limerick, MOCK_CLEANSE_CONFIG)

        assert result[0] == "You can get a good deal from rehearsal"
        assert result[1] == "If it just has the proper dispersal.Y"
        assert result[2] == f"{INDENT_HTML_START}You would just be an ass{INDENT_HTML_END}"
        assert result[3] == f"{INDENT_HTML_START}To do it en masse,{INDENT_HTML_END}"
        assert result[4] == "Your remembering would turn out much worsal.X"

    
    def test_line_comment(self):
        limerick = dedent("""
        Here is a line # with a comment
        And a second line.
        """).strip()
        result = cleanse_text(limerick, MOCK_CLEANSE_CONFIG)

        assert result[0] == "Here is a line"
        assert result[1] == "And a second line.X"
    

test_poem = dedent("""
    # Samuel Longfellow
    'Tis winter now; the fallen snow
    Has left the heavens all coldly clear;
    Through leafless boughs the sharp winds blow,
    And all the earth lies dead and drear.

    And yet God's love is not withdrawn;
    His life within the keen air breathes;
    God's beauty paints the crimson dawn,
    And clothes the boughs with glittering wreaths.

    And though abroad the sharp winds blow,
    And skies are chill, and frosts are keen,
    Home closer draws her circle now,
    And warmer glows her light within.

    O God! Who gives the winter's cold
    As well as summer's joyous rays,
    Us warmly in Thy love enfold,
    And keep us through life's wintry days.
    """).strip()


class MockModel:
    def __init__(self):
        self.properties = {}

    def __call__(self):
        return self.properties

    def by_name(self, name):
        return self


class MockCollection:
    def __init__(self):
        self.notes = []

    def addNote(self, note):
        self.notes.append(note)

    @property
    def models(self):
        return MockModel()


class MockNote:
    def __init__(self, collection, ntype):
        self.collection = collection
        self.note_type = ntype
        self.tags = []
        self.properties = {}

    def __getitem__(self, item):
        return self.properties[item]

    def __setitem__(self, item, value):
        self.properties[item] = value

    def __delitem__(self, item):
        del self.properties[item]

    def __contains__(self, item):
        return item in self.properties


@pytest.fixture
def mock_note():
    col = MockCollection()
    config = {}
    note_constructor = MockNote
    title = "'Tis Winter"
    tags = ["poem", "test"]
    deck_id = 1
    context_lines = 2
    recite_lines = 1
    group_lines = 1
    step = 1
    media = []
    media_mode = MediaImportMode.BULK
    mode = ImportMode.CUSTOM
    caesura = '**'
    text = cleanse_text(test_poem, MOCK_CLEANSE_CONFIG)
    return dict(locals())


def test_render_default_settings(mock_note):
    col = mock_note['col']
    num_added = add_notes(**mock_note)

    assert num_added == 16
    assert len(col.notes) == 16

    assert col.notes[0]['العنوان'] == mock_note['title']
    assert col.notes[0].tags == mock_note['tags']
    assert col.notes[0]['الرقم'] == "1"
    assert col.notes[0]['السياق'] == "<p>[البداية]</p>"
    assert col.notes[0]['الأبيات'] == "<p>'Tis winter now; the fallen snow</p>"
    assert 'محث' not in col.notes[0]

    assert col.notes[3]['العنوان'] == mock_note['title']
    assert col.notes[3].tags == mock_note['tags']
    assert col.notes[3]['الرقم'] == "4"
    assert col.notes[3]['السياق'] == (
        "<p>Has left the heavens all coldly clear;</p>"
        "<p>Through leafless boughs the sharp winds blow,</p>"
    )
    assert col.notes[3]['الأبيات'] == "<p>And all the earth lies dead and drear.Y</p>"
    assert 'محث' not in col.notes[3]


### GROUPS ###
def test_render_groups_of_two(mock_note):
    col = mock_note['col']
    mock_note['group_lines'] = 2
    num_added = add_notes(**mock_note)

    assert num_added == 8
    assert len(col.notes) == 8

    # We won't bother testing title and tags for further items.
    assert col.notes[0]['الرقم'] == "1"
    assert col.notes[0]['السياق'] == "<p>[البداية]</p>"
    assert col.notes[0]['الأبيات'] == (
        "<p>'Tis winter now; the fallen snow</p>"
        "<p>Has left the heavens all coldly clear;</p>"
    )
    assert col.notes[0]['محث'] == "[...2]"

    assert col.notes[1]['الرقم'] == "2"
    assert col.notes[1]['السياق'] == (
        "<p>[البداية]</p>"
        "<p>'Tis winter now; the fallen snow</p>"
        "<p>Has left the heavens all coldly clear;</p>"
    )
    assert col.notes[1]['الأبيات'] == (
        "<p>Through leafless boughs the sharp winds blow,</p>"
        "<p>And all the earth lies dead and drear.Y</p>"
    )
    assert col.notes[1]['محث'] == "[...2]"


def test_render_groups_of_three(mock_note):
    col = mock_note['col']
    mock_note['group_lines'] = 3
    num_added = add_notes(**mock_note)

    assert num_added == 6
    assert len(col.notes) == 6

    assert col.notes[0]['العنوان'] == mock_note['title']
    assert col.notes[0].tags == mock_note['tags']
    assert col.notes[0]['الرقم'] == "1"
    assert col.notes[0]['السياق'] == "<p>[البداية]</p>"
    assert col.notes[0]['الأبيات'] == (
        "<p>'Tis winter now; the fallen snow</p>"
        "<p>Has left the heavens all coldly clear;</p>"
        "<p>Through leafless boughs the sharp winds blow,</p>"
    )
    assert col.notes[0]['محث'] == "[...3]"

    # Last item has six lines of context but only one recitation line, with no prompt
    # (as 16 % 3 = 1).
    assert col.notes[5]['الرقم'] == "6"
    assert col.notes[5]['السياق'] == (
        "<p>And skies are chill, and frosts are keen,</p>"
        "<p>Home closer draws her circle now,</p>"
        "<p>And warmer glows her light within.Y</p>"
        "<p>O God! Who gives the winter's cold</p>"
        "<p>As well as summer's joyous rays,</p>"
        "<p>Us warmly in Thy love enfold,</p>"
    )
    assert col.notes[5]['الأبيات'] == "<p>And keep us through life's wintry days.X</p>"
    assert 'محث' not in col.notes[5], col.notes[5]['محث']


### CONTEXT LINES ###
def test_render_three_context_lines(mock_note):
    col = mock_note['col']
    mock_note['context_lines'] = 3
    num_added = add_notes(**mock_note)

    assert num_added == 16
    assert len(col.notes) == 16

    assert col.notes[0]['الرقم'] == "1"
    assert col.notes[0]['السياق'] == "<p>[البداية]</p>"
    assert col.notes[0]['الأبيات'] == "<p>'Tis winter now; the fallen snow</p>"
    assert 'محث' not in col.notes[0]

    assert col.notes[1]['السياق'] == (
        "<p>[البداية]</p>"
        "<p>'Tis winter now; the fallen snow</p>"
    )
    assert col.notes[1]['الأبيات'] == "<p>Has left the heavens all coldly clear;</p>"

    assert col.notes[2]['السياق'] == (
        "<p>[البداية]</p>"
        "<p>'Tis winter now; the fallen snow</p>"
        "<p>Has left the heavens all coldly clear;</p>"
    )
    assert col.notes[2]['الأبيات'] == "<p>Through leafless boughs the sharp winds blow,</p>"

    assert col.notes[3]['السياق'] == (
        "<p>'Tis winter now; the fallen snow</p>"
        "<p>Has left the heavens all coldly clear;</p>"
        "<p>Through leafless boughs the sharp winds blow,</p>"
    )
    assert col.notes[3]['الأبيات'] == "<p>And all the earth lies dead and drear.Y</p>"

    assert col.notes[4]['السياق'] == (
        "<p>Has left the heavens all coldly clear;</p>"
        "<p>Through leafless boughs the sharp winds blow,</p>"
        "<p>And all the earth lies dead and drear.Y</p>"
    )
    assert col.notes[4]['الأبيات'] == "<p>And yet God's love is not withdrawn;</p>"


### RECITATION LINES ###
def test_render_two_recitation_lines(mock_note):
    col = mock_note['col']
    mock_note['recite_lines'] = 2
    num_added = add_notes(**mock_note)

    # Unlike grouping, having more recitation lines involves overlap,
    # so there are still 16 notes.
    assert num_added == 16
    assert len(col.notes) == 16

    assert col.notes[0]['السياق'] == "<p>[البداية]</p>"
    assert col.notes[0]['الأبيات'] == (
        "<p>'Tis winter now; the fallen snow</p>"
        "<p>Has left the heavens all coldly clear;</p>"
    )
    assert col.notes[0]['محث'] == "[...2]"

    assert col.notes[1]['السياق'] == (
        "<p>[البداية]</p>"
        "<p>'Tis winter now; the fallen snow</p>"
    )
    assert col.notes[1]['الأبيات'] == (
        "<p>Has left the heavens all coldly clear;</p>"
        "<p>Through leafless boughs the sharp winds blow,</p>"
    )

    assert col.notes[2]['السياق'] == (
        "<p>'Tis winter now; the fallen snow</p>"
        "<p>Has left the heavens all coldly clear;</p>"
    )
    assert col.notes[2]['الأبيات'] == (
        "<p>Through leafless boughs the sharp winds blow,</p>"
        "<p>And all the earth lies dead and drear.Y</p>"
    )

    # The very last line will request a single recitation.
    assert col.notes[-1]['السياق'] == (
        "<p>As well as summer's joyous rays,</p>"
        "<p>Us warmly in Thy love enfold,</p>"
    )
    assert col.notes[-1]['الأبيات'] == "<p>And keep us through life's wintry days.X</p>"
    assert 'محث' not in col.notes[-1]


### TRIPLE PLAY ###
def test_render_increase_all_options(mock_note):
    """
    In this configuration, we have lines grouped into sets of 2 -- so 8
    virtual lines -- and then we show 3 virtual lines as context (6 physical
    lines) and request 2 virtual lines for recitation (4 physical lines).
    """
    col = mock_note['col']
    mock_note['context_lines'] = 3
    mock_note['recite_lines'] = 2
    mock_note['group_lines'] = 2
    num_added = add_notes(**mock_note)

    # Only grouping reduces the number; the other parameters cause only
    # additional overlap.
    assert num_added == 8
    assert len(col.notes) == 8

    assert col.notes[0]['السياق'] == "<p>[البداية]</p>"
    assert col.notes[0]['الأبيات'] == (
        "<p>'Tis winter now; the fallen snow</p>"
        "<p>Has left the heavens all coldly clear;</p>"
        "<p>Through leafless boughs the sharp winds blow,</p>"
        "<p>And all the earth lies dead and drear.Y</p>"
    )
    assert col.notes[0]['محث'] == "[...4]"

    assert col.notes[1]['السياق'] == (
        "<p>[البداية]</p>"
        "<p>'Tis winter now; the fallen snow</p>"
        "<p>Has left the heavens all coldly clear;</p>"
    )
    assert col.notes[1]['الأبيات'] == (
        "<p>Through leafless boughs the sharp winds blow,</p>"
        "<p>And all the earth lies dead and drear.Y</p>"
        "<p>And yet God's love is not withdrawn;</p>"
        "<p>His life within the keen air breathes;</p>"
    )
    assert col.notes[1]['محث'] == "[...4]"

    assert col.notes[2]['السياق'] == (
        "<p>[البداية]</p>"
        "<p>'Tis winter now; the fallen snow</p>"
        "<p>Has left the heavens all coldly clear;</p>"
        "<p>Through leafless boughs the sharp winds blow,</p>"
        "<p>And all the earth lies dead and drear.Y</p>"
    )
    assert col.notes[2]['الأبيات'] == (
        "<p>And yet God's love is not withdrawn;</p>"
        "<p>His life within the keen air breathes;</p>"
        "<p>God's beauty paints the crimson dawn,</p>"
        "<p>And clothes the boughs with glittering wreaths.Y</p>"
    )
    assert col.notes[2]['محث'] == "[...4]"

    assert col.notes[3]['السياق'] == (
        "<p>'Tis winter now; the fallen snow</p>"
        "<p>Has left the heavens all coldly clear;</p>"
        "<p>Through leafless boughs the sharp winds blow,</p>"
        "<p>And all the earth lies dead and drear.Y</p>"
        "<p>And yet God's love is not withdrawn;</p>"
        "<p>His life within the keen air breathes;</p>"
    )
    assert col.notes[3]['الأبيات'] == (
        "<p>God's beauty paints the crimson dawn,</p>"
        "<p>And clothes the boughs with glittering wreaths.Y</p>"
        "<p>And though abroad the sharp winds blow,</p>"
        "<p>And skies are chill, and frosts are keen,</p>"
    )
    assert col.notes[3]['محث'] == "[...4]"

    assert col.notes[6]['السياق'] == (
        "<p>God's beauty paints the crimson dawn,</p>"
        "<p>And clothes the boughs with glittering wreaths.Y</p>"
        "<p>And though abroad the sharp winds blow,</p>"
        "<p>And skies are chill, and frosts are keen,</p>"
        "<p>Home closer draws her circle now,</p>"
        "<p>And warmer glows her light within.Y</p>"
    )
    assert col.notes[6]['الأبيات'] == (
        "<p>O God! Who gives the winter's cold</p>"
        "<p>As well as summer's joyous rays,</p>"
        "<p>Us warmly in Thy love enfold,</p>"
        "<p>And keep us through life's wintry days.X</p>"
    )
    assert col.notes[6]['محث'] == "[...4]"

    assert col.notes[7]['السياق'] == (
        "<p>And though abroad the sharp winds blow,</p>"
        "<p>And skies are chill, and frosts are keen,</p>"
        "<p>Home closer draws her circle now,</p>"
        "<p>And warmer glows her light within.Y</p>"
        "<p>O God! Who gives the winter's cold</p>"
        "<p>As well as summer's joyous rays,</p>"
    )
    assert col.notes[7]['الأبيات'] == (
        "<p>Us warmly in Thy love enfold,</p>"
        "<p>And keep us through life's wintry days.X</p>"
    )
    assert col.notes[7]['محث'] == "[...2]"

def test_render_steps(mock_note):

    col = mock_note['col']
    mock_note['step'] = 2
    num_added = add_notes(**mock_note)

    assert num_added == 8
    assert len(col.notes) == 8

    assert col.notes[0]['العنوان'] == mock_note['title']
    assert col.notes[0].tags == mock_note['tags']
    assert col.notes[0]['الرقم'] == "1"
    assert col.notes[0]['السياق'] == "<p>[البداية]</p>"
    assert col.notes[0]['الأبيات'] == "<p>'Tis winter now; the fallen snow</p>"
    assert 'محث' not in col.notes[0]

    assert col.notes[3]['العنوان'] == mock_note['title']
    assert col.notes[3].tags == mock_note['tags']
    assert col.notes[3]['الرقم'] == "4"
    assert col.notes[3]['السياق'] == (
        "<p>And yet God's love is not withdrawn;</p>"
        "<p>His life within the keen air breathes;</p>"
    )
    assert col.notes[3]['الأبيات'] == "<p>God's beauty paints the crimson dawn,</p>"
    assert 'محث' not in col.notes[3]


automatic_test_poem = dedent("""
    مَتْنُ نَظْمِ الْآجُرٌّومِيَّة
    1. قَـالَ عُبَيْدُ رَبِهِ مُحَـمَّدُ ** اللهَ فِي كُـلِّ الأُمُـورِ أَحْـمَد
    2. مُصَلِّـيًا عَلَى الرَّسُولِ المُنْتَقَى ** وَآلِـهِ وَصَحْـبِهِ ذَوِي التُّـقَى
    3. وَبَعْـدُ فَالقَصْـدُ بِذَا المَنْظُومِ ** تَسْهِيلُ مَنْـثُورِ ابْـنِ آجُـرُّومِ
    4. لِـمَنْ أَرَادَ حِفْـظَهُ وَعَسُرَا ** عَلَيْهِ أَنْ يَحْـفَظَ مَـا قَـدْ نُثِرَا
    5. واللهَ أَسْتَعِـينُ فِي كُلِّ عَمَلْ ** إِلَيْهِ قَصْـدِي وَعَلَـيْهِ المُتَّـكَلْ
    بَابُ الكَلاَمِ
    6. إِنَّ الكَلاَمَ عِنْـدَنَا فَلْتَسْتَمِعْ ** لَفْظٌ مُـرَكَّبٌ مُفِـيدٌ قَـدْ وُضِعْ
    7. أَقْسَـامُهُ الَّتِي عَـلَيْهَا يُبْنَى ** اِسْمٌ وَفِعْـلٌ ثُمَّ حَـرْفُ مَـعْنَى
    8. فَالاِسْمُ بِالخَفْضِ وَبِالتَّنْوِينِ أَوْ ** دُخُولِ «أَلْ» يُعْرَفُ فَاقْفُ مَا قَفَوا
    9. وَبِحُرُوفِ الخّفْضِ وَهْيَ مِنْ، إِلَى ** وَعَنْ، وَفِي، وَرُبَّ، وَالبَا، وَعَلَى
    10.وَالكَافُ، والَّلاَمُ، وَوَاوٌ، وَالتَّا ** وَمُذْ، وَمُنْذُ، وَلَعَلّ، حَتَّى
    11. وَالفِعْلُ بِالسِّينِ، وَسَوْفَ، وَبِقَدْ ** فَاعْلَمْ، وَتَا التَّأْنِيثِ، مَيْزُهُ وَرَدْ
    12. وَالحَرْفُ يُعْـرَفُ بِأَلاَّ يَقْبَلاَ ** لاِسْمٍ وَلاَ فِعْلٍ دَلِيلاً كَـ «بَلَى»
    بَابُ الإِعْرَابِ
    13- الاِعْرَابُ تَغْييرُ أَوَاخِرِ الكَلِمْ ** تَقْدِيرًا اوْ لَفْظًا فَذَا الحَدَّ اغْتَنِم
    14- وَذَلِكَ التَّغْيِيرُ لاِضْطِرَابِ ** عَوَامِلٍ تَدْخُلُ لِلإِعْرَابِ
    15- أقْسَامُهُ أَرْبَعَةٌ تُؤَمُّ ** رَفْـعٌ، وَنَصْـبٌ، ثُمَّ خَفْضٌ، جَـزْمُ
    16- فَالأَوَّلاَنِ دُونَ رَيْبٍ وَقَعَا ** فِي الاِسْمِ وَالفِعْلِ المُضَارِعِ مَعَا
    17- وَالاِسْمُ قَدْ خُصِّصَ بِالخّفْضِ كَمَا ** قَدْ خُصِّصَ الفِعْلُ بِجَزْمٍ فَاعْلَمَا
    """).strip()


def test_render_automatic(mock_note):
    """
    Test the so-called automatic mode where title and subtitles interspersed in the peom text are recognized
    and verses are expected to be numbered.
    """

    col = mock_note['col']
    mock_note['step'] = 3
    mock_note['title'] = 'مَتْنُ نَظْمِ الْآجُرٌّومِيَّة'
    mock_note['text'] = cleanse_text(automatic_test_poem, MOCK_CLEANSE_CONFIG)
    mock_note['mode'] = ImportMode.AUTOMATIC
    num_added = add_notes(**mock_note)

    assert num_added == 6
    assert len(col.notes) == 6

    assert col.notes[0]['العنوان'] == mock_note['title']
    assert col.notes[0]['الباب'] == ''
    assert col.notes[0]['الرقم'] == '1'
    assert col.notes[0]['الحالي'] == '1'
    assert col.notes[0]['السياق'] == "<p>[البداية]</p>"
    assert col.notes[0]['الأبيات'] == "<p>1. قَـالَ عُبَيْدُ رَبِهِ مُحَـمَّدُ ** اللهَ فِي كُـلِّ الأُمُـورِ أَحْـمَد</p>"
    assert 'محث' not in col.notes[0]

    assert col.notes[2]['العنوان'] == mock_note['title']
    assert col.notes[2]['الباب'] == '<p>بَابُ الكَلاَمِ</p>'
    assert col.notes[2]['الرقم'] == '3'
    assert col.notes[2]['الحالي'] == '7'
    assert col.notes[2]['السياق'] == (
        "<p>5. واللهَ أَسْتَعِـينُ فِي كُلِّ عَمَلْ ** إِلَيْهِ قَصْـدِي وَعَلَـيْهِ المُتَّـكَلْ</p>"
        "<p>6. إِنَّ الكَلاَمَ عِنْـدَنَا فَلْتَسْتَمِعْ ** لَفْظٌ مُـرَكَّبٌ مُفِـيدٌ قَـدْ وُضِعْ</p>"
    )
    assert col.notes[2]['الأبيات'] == "<p>7. أَقْسَـامُهُ الَّتِي عَـلَيْهَا يُبْنَى ** اِسْمٌ وَفِعْـلٌ ثُمَّ حَـرْفُ مَـعْنَى</p>"

    assert col.notes[4]['العنوان'] == mock_note['title']
    assert col.notes[4]['الباب'] == '<p>بَابُ الكَلاَمِ</p><p>بَابُ الإِعْرَابِ</p>'
    assert col.notes[4]['الرقم'] == '5'
    assert col.notes[4]['الحالي'] == '13'
    assert col.notes[4]['السياق'] == (
        "<p>11. وَالفِعْلُ بِالسِّينِ، وَسَوْفَ، وَبِقَدْ ** فَاعْلَمْ، وَتَا التَّأْنِيثِ، مَيْزُهُ وَرَدْ</p>"
        "<p>12. وَالحَرْفُ يُعْـرَفُ بِأَلاَّ يَقْبَلاَ ** لاِسْمٍ وَلاَ فِعْلٍ دَلِيلاً كَـ «بَلَى»</p>"
    )
    assert col.notes[4]['الأبيات'] == "<p>13- الاِعْرَابُ تَغْييرُ أَوَاخِرِ الكَلِمْ ** تَقْدِيرًا اوْ لَفْظًا فَذَا الحَدَّ اغْتَنِم</p>"


def test_render_automatic_groups(mock_note):

    col = mock_note['col']
    mock_note['group_lines'] = 2
    mock_note['context_lines'] = 1
    mock_note['title'] = 'مَتْنُ نَظْمِ الْآجُرٌّومِيَّة'
    mock_note['text'] = cleanse_text(automatic_test_poem, MOCK_CLEANSE_CONFIG)
    mock_note['mode'] = ImportMode.AUTOMATIC
    num_added = add_notes(**mock_note)

    assert num_added == 9
    assert len(col.notes) == 9

    assert col.notes[6]['محث'] == "[...2]"
    assert col.notes[6]['العنوان'] == mock_note['title']
    assert col.notes[6]['الباب'] == '<p>بَابُ الكَلاَمِ</p><p>بَابُ الإِعْرَابِ</p>'
    assert col.notes[6]['الرقم'] == '7'
    assert col.notes[6]['الحالي'] == '13'
    assert col.notes[6]['السياق'] == (
        "<p>11. وَالفِعْلُ بِالسِّينِ، وَسَوْفَ، وَبِقَدْ ** فَاعْلَمْ، وَتَا التَّأْنِيثِ، مَيْزُهُ وَرَدْ</p>"
        "<p>12. وَالحَرْفُ يُعْـرَفُ بِأَلاَّ يَقْبَلاَ ** لاِسْمٍ وَلاَ فِعْلٍ دَلِيلاً كَـ «بَلَى»</p>"
    )
    assert col.notes[6]['الأبيات'] == (
        "<p>13- الاِعْرَابُ تَغْييرُ أَوَاخِرِ الكَلِمْ ** تَقْدِيرًا اوْ لَفْظًا فَذَا الحَدَّ اغْتَنِم</p>"
        "<p>14- وَذَلِكَ التَّغْيِيرُ لاِضْطِرَابِ ** عَوَامِلٍ تَدْخُلُ لِلإِعْرَابِ</p>"
    )

def test_render_automatic_groups_with_steps(mock_note):

    col = mock_note['col']
    mock_note['group_lines'] = 2
    mock_note['context_lines'] = 1
    mock_note['step'] = 2
    mock_note['title'] = 'مَتْنُ نَظْمِ الْآجُرٌّومِيَّة'
    mock_note['text'] = cleanse_text(automatic_test_poem, MOCK_CLEANSE_CONFIG)
    mock_note['mode'] = ImportMode.AUTOMATIC
    num_added = add_notes(**mock_note)

    assert num_added == 5
    assert len(col.notes) == 5

    assert col.notes[0]['محث'] == "[...2]"
    assert 'محث' not in col.notes[4]
    assert col.notes[3]['العنوان'] == mock_note['title']
    assert col.notes[3]['الباب'] == '<p>بَابُ الكَلاَمِ</p><p>بَابُ الإِعْرَابِ</p>'
    assert col.notes[3]['الرقم'] == '4'
    assert col.notes[3]['الحالي'] == '13'
    assert col.notes[3]['السياق'] == (
        "<p>11. وَالفِعْلُ بِالسِّينِ، وَسَوْفَ، وَبِقَدْ ** فَاعْلَمْ، وَتَا التَّأْنِيثِ، مَيْزُهُ وَرَدْ</p>"
        "<p>12. وَالحَرْفُ يُعْـرَفُ بِأَلاَّ يَقْبَلاَ ** لاِسْمٍ وَلاَ فِعْلٍ دَلِيلاً كَـ «بَلَى»</p>"
    )
    assert col.notes[3]['الأبيات'] == (
        "<p>13- الاِعْرَابُ تَغْييرُ أَوَاخِرِ الكَلِمْ ** تَقْدِيرًا اوْ لَفْظًا فَذَا الحَدَّ اغْتَنِم</p>"
        "<p>14- وَذَلِكَ التَّغْيِيرُ لاِضْطِرَابِ ** عَوَامِلٍ تَدْخُلُ لِلإِعْرَابِ</p>"
    )

def test_render_by_section(mock_note):

    col = mock_note['col']
    mock_note['title'] = 'مَتْنُ نَظْمِ الْآجُرٌّومِيَّة'
    mock_note['text'] = cleanse_text(automatic_test_poem, MOCK_CLEANSE_CONFIG)
    mock_note['mode'] = ImportMode.BY_SECTION
    num_added = add_notes(**mock_note)

    assert num_added == 3
    assert len(col.notes) == 3

    assert col.notes[0]['محث'] == "[...5]"
    assert col.notes[1]['محث'] == "[...7]"
    assert col.notes[2]['محث'] == "[...5]"

    assert col.notes[0]['العنوان'] == mock_note['title']
    assert col.notes[0]['الباب'] == ''
    assert col.notes[1]['الباب'] == ''
    assert col.notes[2]['الباب'] == ''

    assert col.notes[0]['السياق'] == '<p></p>'
    assert col.notes[1]['السياق'] == '<p>بَابُ الكَلاَمِ</p>'
    assert col.notes[2]['السياق'] == '<p>بَابُ الإِعْرَابِ</p>'

    assert col.notes[0]['الحالي'] == '1'
    assert col.notes[0]['الأبيات'] == (
        "<p>1. قَـالَ عُبَيْدُ رَبِهِ مُحَـمَّدُ ** اللهَ فِي كُـلِّ الأُمُـورِ أَحْـمَد</p>"
        "<p>2. مُصَلِّـيًا عَلَى الرَّسُولِ المُنْتَقَى ** وَآلِـهِ وَصَحْـبِهِ ذَوِي التُّـقَى</p>"
        "<p>3. وَبَعْـدُ فَالقَصْـدُ بِذَا المَنْظُومِ ** تَسْهِيلُ مَنْـثُورِ ابْـنِ آجُـرُّومِ</p>"
        "<p>4. لِـمَنْ أَرَادَ حِفْـظَهُ وَعَسُرَا ** عَلَيْهِ أَنْ يَحْـفَظَ مَـا قَـدْ نُثِرَا</p>"
        "<p>5. واللهَ أَسْتَعِـينُ فِي كُلِّ عَمَلْ ** إِلَيْهِ قَصْـدِي وَعَلَـيْهِ المُتَّـكَلْ</p>"
    )
    assert col.notes[1]['الحالي'] == '6'
    assert col.notes[1]['الأبيات'] == (
        "<p>6. إِنَّ الكَلاَمَ عِنْـدَنَا فَلْتَسْتَمِعْ ** لَفْظٌ مُـرَكَّبٌ مُفِـيدٌ قَـدْ وُضِعْ</p>"
        "<p>7. أَقْسَـامُهُ الَّتِي عَـلَيْهَا يُبْنَى ** اِسْمٌ وَفِعْـلٌ ثُمَّ حَـرْفُ مَـعْنَى</p>"
        "<p>8. فَالاِسْمُ بِالخَفْضِ وَبِالتَّنْوِينِ أَوْ ** دُخُولِ «أَلْ» يُعْرَفُ فَاقْفُ مَا قَفَوا</p>"
        "<p>9. وَبِحُرُوفِ الخّفْضِ وَهْيَ مِنْ، إِلَى ** وَعَنْ، وَفِي، وَرُبَّ، وَالبَا، وَعَلَى</p>"
        "<p>10.وَالكَافُ، والَّلاَمُ، وَوَاوٌ، وَالتَّا ** وَمُذْ، وَمُنْذُ، وَلَعَلّ، حَتَّى</p>"
        "<p>11. وَالفِعْلُ بِالسِّينِ، وَسَوْفَ، وَبِقَدْ ** فَاعْلَمْ، وَتَا التَّأْنِيثِ، مَيْزُهُ وَرَدْ</p>"
        "<p>12. وَالحَرْفُ يُعْـرَفُ بِأَلاَّ يَقْبَلاَ ** لاِسْمٍ وَلاَ فِعْلٍ دَلِيلاً كَـ «بَلَى»</p>"

    )
    assert col.notes[2]['الحالي'] == '13'
    assert col.notes[2]['الأبيات'] == (
        "<p>13- الاِعْرَابُ تَغْييرُ أَوَاخِرِ الكَلِمْ ** تَقْدِيرًا اوْ لَفْظًا فَذَا الحَدَّ اغْتَنِم</p>"
        "<p>14- وَذَلِكَ التَّغْيِيرُ لاِضْطِرَابِ ** عَوَامِلٍ تَدْخُلُ لِلإِعْرَابِ</p>"
        "<p>15- أقْسَامُهُ أَرْبَعَةٌ تُؤَمُّ ** رَفْـعٌ، وَنَصْـبٌ، ثُمَّ خَفْضٌ، جَـزْمُ</p>"
        "<p>16- فَالأَوَّلاَنِ دُونَ رَيْبٍ وَقَعَا ** فِي الاِسْمِ وَالفِعْلِ المُضَارِعِ مَعَا</p>"
        "<p>17- وَالاِسْمُ قَدْ خُصِّصَ بِالخّفْضِ كَمَا ** قَدْ خُصِّصَ الفِعْلُ بِجَزْمٍ فَاعْلَمَاX</p>"
    )

def test_render_media(mock_note):

    col = mock_note['col']
    mock_note['title'] = 'مَتْنُ نَظْمِ الْآجُرٌّومِيَّة'
    mock_note['text'] = cleanse_text(automatic_test_poem, MOCK_CLEANSE_CONFIG)
    mock_note['mode'] = ImportMode.BY_SECTION
    mock_note['media'] = [
        '1.mp3', '2.mp3', '3.mp3', '4.mp3', '5.mp3',
        '6.mp3', '7.mp3', '8.mp3', '9.mp3', '10.mp3',
        '11.mp3', '12.mp3'
    ]
    num_added = add_notes(**mock_note)

    assert col.notes[0]['وسائط'] == ''.join(mock_note['media'])
    assert col.notes[1]['وسائط'] == ''.join(mock_note['media'])
    assert col.notes[2]['وسائط'] == ''.join(mock_note['media'])

    col.notes = []
    mock_note['media_mode'] = MediaImportMode.ONE_FOR_EACH_NOTE
    num_added = add_notes(**mock_note)
    assert col.notes[0]['وسائط'] == '1.mp3'
    assert col.notes[1]['وسائط'] == '2.mp3'
    assert col.notes[2]['وسائط'] == '3.mp3'

    col.notes = []
    mock_note['media_mode'] = MediaImportMode.BY_RECITE_LINES
    num_added = add_notes(**mock_note)
    for i in range(5):
        assert mock_note['media'][i] in col.notes[0]['وسائط']

    # media distribution with custom step
    col.notes = []
    mock_note['media_mode'] = MediaImportMode.BY_RECITE_LINES
    mock_note['mode'] = ImportMode.CUSTOM
    mock_note['step'] = 3
    mock_note['recite_lines'] = 2
    num_added = add_notes(**mock_note)
    assert '1.mp3' in col.notes[0]['وسائط']
    assert '2.mp3' in col.notes[0]['وسائط']
    assert '4.mp3' in col.notes[1]['وسائط']
    assert '5.mp3' in col.notes[1]['وسائط']
    assert '7.mp3' in col.notes[2]['وسائط']

    # custom step + line groups
    col.notes = []
    mock_note['media_mode'] = MediaImportMode.ONE_FOR_EACH_NOTE
    mock_note['mode'] = ImportMode.CUSTOM
    mock_note['step'] = 3
    mock_note['recite_lines'] = 2
    mock_note['group_lines'] = 2
    add_notes(**mock_note)
    assert '1.mp3' in col.notes[0]['وسائط']
    assert '4.mp3' in col.notes[1]['وسائط']
    assert '7.mp3' in col.notes[2]['وسائط']

    # custom step + line groups + media distribution by recitation lines
    col.notes = []
    mock_note['media_mode'] = MediaImportMode.BY_RECITE_LINES
    mock_note['mode'] = ImportMode.CUSTOM
    mock_note['step'] = 3
    mock_note['recite_lines'] = 2
    mock_note['group_lines'] = 2
    add_notes(**mock_note)
    assert '1.mp3' in col.notes[0]['وسائط']
    assert '2.mp3' in col.notes[0]['وسائط']
    assert '4.mp3' in col.notes[1]['وسائط']
    assert '5.mp3' in col.notes[1]['وسائط']
    assert '7.mp3' in col.notes[2]['وسائط']

    # media distribution by the number of lines of each section
    col.notes = []
    mock_note['media_mode'] = MediaImportMode.BY_RECITE_LINES
    mock_note['mode'] = ImportMode.BY_SECTION
    add_notes(**mock_note)
    for i in range(1, 6):
        assert f'{i}.mp3' in col.notes[0]['وسائط']
    for i in range(6, 13):
        assert f'{i}.mp3' in col.notes[1]['وسائط']

    # one media file for each section
    col.notes = []
    mock_note['media_mode'] = MediaImportMode.ONE_FOR_EACH_NOTE
    mock_note['mode'] = ImportMode.BY_SECTION
    add_notes(**mock_note)
    for i in range(len(col.notes)):
        assert mock_note['media'][i] in col.notes[i]['وسائط']


def test_parse_custom_caesura():

    parsed = automatic_parse_text(cleanse_text(automatic_test_poem.replace("**", "//"), MOCK_CLEANSE_CONFIG), "//")
    assert parsed['title'] == "مَتْنُ نَظْمِ الْآجُرٌّومِيَّة"
    for i in range(5):
        assert parsed['subtitles'][i] == ''
    for i in range(5, 12):
        assert parsed['subtitles'][i] == 'بَابُ الكَلاَمِ'
    for i in range(12, 17):
        assert parsed['subtitles'][i] == 'بَابُ الإِعْرَابِ'

    assert parsed['verses'][0] == '1. قَـالَ عُبَيْدُ رَبِهِ مُحَـمَّدُ // اللهَ فِي كُـلِّ الأُمُـورِ أَحْـمَد'
    assert parsed['verses'][5] == '6. إِنَّ الكَلاَمَ عِنْـدَنَا فَلْتَسْتَمِعْ // لَفْظٌ مُـرَكَّبٌ مُفِـيدٌ قَـدْ وُضِعْ'
    assert parsed['verses'][12] == '13- الاِعْرَابُ تَغْييرُ أَوَاخِرِ الكَلِمْ // تَقْدِيرًا اوْ لَفْظًا فَذَا الحَدَّ اغْتَنِم'
    assert parsed['verses'][16] == '17- وَالاِسْمُ قَدْ خُصِّصَ بِالخّفْضِ كَمَا // قَدْ خُصِّصَ الفِعْلُ بِجَزْمٍ فَاعْلَمَاX'
