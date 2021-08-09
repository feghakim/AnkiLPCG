"""
trmodels.py - self-constructing definitions of Anki models (note types)

Creating a note type in Anki is a procedural operation, which is inconvenient
and difficult to read when note types need to be defined in source code
rather than through the GUI. This module allows note types to be defined
declaratively.

It first defines TemplateData and ModelData classes which contain the logic
for creating templates and note types, then subclasses which define the
options and templates for each note type our application needs to create and
manage. A framework for checking if note types exist and have the expected
fields, and for changing between note types defined here, is also provided.

These classes are a bit unusual in that they are never instantiated and have
no instance methods or variables. The class structure is just used as a
convenient way to inherit construction logic and fields and group related
information together.

This mini-framework was originally created for TiddlyRemember and is
presented in slightly altered form here. The third project should combine the
two versions and create a standardized system!
"""
from abc import ABC
from textwrap import dedent
from typing import Callable, Dict, Tuple, Type
import os

import aqt
from aqt.utils import askUser, showInfo
from anki.consts import MODEL_CLOZE


class TemplateData(ABC):
    """
    Self-constructing definition for templates.
    """
    name: str
    front: str
    back: str

    @classmethod
    def to_template(cls) -> Dict:
        "Create and return an Anki template object for this model definition."
        assert aqt.mw is not None, "Tried to use models before Anki is initialized!"
        mm = aqt.mw.col.models
        t = mm.newTemplate(cls.name)
        t['qfmt'] = dedent(cls.front).strip()
        t['afmt'] = dedent(cls.back).strip()
        return t


class ModelData(ABC):
    """
    Self-constructing definition for models.
    """
    name: str
    fields: Tuple[str, ...]
    templates: Tuple[Type[TemplateData]]
    styling: str
    sort_field: str
    is_cloze: bool
    version: str
    upgrades: Tuple[Tuple[str, str, Callable[[Dict], None]], ...]

    @classmethod
    def to_model(cls) -> Tuple[Dict, str]:
        """
        Create and return a pair of (Anki model object, version spec)
        for this model definition.
        """
        assert aqt.mw is not None, "Tried to use models before Anki is initialized!"
        mm = aqt.mw.col.models
        model = mm.new(cls.name)
        for i in cls.fields:
            field = mm.newField(i)
            field["rtl"] = True
            mm.addField(model, field)
        for template in cls.templates:
            t = template.to_template()
            mm.addTemplate(model, t)
        model['css'] = dedent(cls.styling).strip()
        model['sortf'] = cls.fields.index(cls.sort_field)
        if cls.is_cloze:
            model['type'] = MODEL_CLOZE
        return model, cls.version

    @classmethod
    def upgrade_from(cls, current_version: str) -> str:
        """
        Given that the model is at version current_version (typically stored
        in the add-on config), run all functions possible in the updates tuple
        of the model. The updates tuple must be presented in chronological order;
        each element is itself a 3-element tuple:

        [0] Version number to upgrade from
        [1] Version number to upgrade to
        [2] Function taking one argument, the model, and mutating it as required;
            raises an exception if update failed.

        Returns the new version the model is at.
        """
        assert aqt.mw is not None, "Tried to use models before Anki is initialized!"
        model = aqt.mw.col.models.byName(cls.name)

        at_version = current_version
        for cur_ver, new_ver, func in cls.upgrades:
            if at_version == cur_ver:
                func(model, cls)
                at_version = new_ver
        if at_version != current_version:
            aqt.mw.col.models.save(model)
        return at_version

    @classmethod
    def in_collection(cls) -> bool:
        """
        Determine if a model by this name exists already in the current
        Anki collection.
        """
        assert aqt.mw is not None, "Tried to use models before Anki is initialized!"
        mm = aqt.mw.col.models
        model = mm.byName(cls.name)
        return model is not None

    @classmethod
    def can_upgrade(cls, current_version: str) -> bool:
        """
        Return True if we know of a newer version of the model than supplied.
        """
        if cls.is_at_version(current_version):
            return False
        for cur_ver, _, __ in cls.upgrades:
            if current_version == cur_ver:
                return True
        return False

    @classmethod
    def is_at_version(cls, current_version: str) -> bool:
        "Return True if this model is at the version current_version."
        return current_version == cls.version


def upgrade_oneohoh_to_oneoneoh(mod, model_data: ModelData):
    "Upgrade ARLPCG model from 1.0.0 to version 1.1.0."
    mm = aqt.mw.col.models
    mm.addField(mod, mm.newField('كامل المنظومة'))

    mod['tmpls'][0]['afmt'] += dedent('''
    <div class="alert extra">
        {{#كامل المنظومة}}
            <div id="hintlink" style="display:none">{{كامل المنظومة}}</div>
            <a href="#" id="show-all">كامل المنظومة</a>
            <br>
        {{/كامل المنظومة}}
    </div>

    <script>
        (function () {
            let hintLink = document.getElementById('hintlink');
            let showAllLink = document.getElementById('show-all');
            showAllLink.addEventListener('click', (e) => {
                showAllLink.style.display = 'none';
                hintLink.style.display = 'block';
                document.getElementById('current').scrollIntoView({behavior: "smooth", inline: "start"});
                e.preventDefault();
            });
        })();
    </script>
    ''').strip()

def upgrade_oneoneoh_to_onetwooh(mod, model_data: ModelData):
    "Store poem texts in the media folder instead of duplicating them in every note, and add repetition counter."
    mm = aqt.mw.col.models
    if 'كامل المنظومة' in mm.field_map(mod):
        mm.removeField(mod, mm.field_map(mod)['كامل المنظومة'][1])
    mm.addField(mod, mm.newField("الحالي"))

    mod['tmpls'][0]['qfmt'] = dedent(model_data.templates[0].front)
    mod['tmpls'][0]['afmt'] = dedent(model_data.templates[0].back)
    mod['css'] = dedent(model_data.styling)

def upgrade_onetwooh_onethreeoh(mod, model_data: ModelData):
    """Add a special field to store a reference the the poem text file
    as a hack so that Anki recognizes it as used and exports it with its deck."""
    mm = aqt.mw.col.models
    mm.addField(mod, mm.newField("خاص (لا تعدل)"))


SRCDIR = os.path.dirname(os.path.realpath(__file__))

class LpcgOne(ModelData):
    class LpcgOneTemplate(TemplateData):
        name = "ARLPCG1"
        front = open(os.path.join(SRCDIR, 'upgrades/1.2.0/front.txt'), encoding='utf-8').read()
        back = open(os.path.join(SRCDIR, 'upgrades/1.2.0/back.txt'), encoding='utf-8').read()

    name = "ARLPCG 1.0"
    fields = ("الأبيات", "السياق", "العنوان", "الباب", "الرقم", "محث", "وسائط", "إضافي", "الحالي", "خاص (لا تعدل)")
    templates = (LpcgOneTemplate,)
    styling = open(os.path.join(SRCDIR, 'upgrades/1.2.0/styling.txt'), encoding='utf-8').read()
    sort_field = "الرقم"
    is_cloze = False
    version = "1.3.0"
    upgrades = (
        ("none", "1.0.0", lambda m, md: None),
        ("1.0.0", "1.1.0", upgrade_oneohoh_to_oneoneoh),
        ("1.1.0", "1.2.0", upgrade_oneoneoh_to_onetwooh),
        ("1.2.0", "1.3.0", upgrade_onetwooh_onethreeoh),
    )


def ensure_note_type() -> None:
    """
    Create or update the LPCG note type as needed.
    """
    assert aqt.mw is not None, "Tried to use models before Anki is initialized!"
    mod = LpcgOne

    if not mod.in_collection():
        model_data, new_version = mod.to_model()
        aqt.mw.col.models.add(model_data)
        aqt.mw.col.set_config('arlpcg_model_version', new_version)
        return

    # "none": the "version number" pre-versioning
    current_version = aqt.mw.col.get_config('arlpcg_model_version', default="none")
    if mod.can_upgrade(current_version):
        r = askUser("لاستيراد ملحوظات جديدة في إصدار ARLPCG هذا، "
                    "يجب تحديث نوع ملحوظات ARLPCG الخاص بك. "
                    "قد يتطلب هذا مزامنة كاملة لمجموعتك بعد الاكتمال. "
                    "هل تريد تحديث نوع الملحوظة الآن؟ "
                    "إذا لم توافق، ستُسأل عندما تشغل أنكي المرة القادمة.")
        if r:
            new_version = mod.upgrade_from(current_version)
            aqt.mw.col.set_config('arlpcg_model_version', new_version)
            showInfo("تم تحديث نوع ملحوظة ARLPCG الخاص بك بنجاح. "
                    "يرجى التأكد من أن بطاقات ARLPCG الخاصة بك "
                    "تظهر بشكل صحيح لكي تستطيع الاسترجاع من نسخة احتياطية "
                    "في حال كان هناك خطب ما.")
        return

    assert mod.is_at_version(aqt.mw.col.get_config('arlpcg_model_version')), \
        "نوع ملحوظات ARLPCG الخاص بك قديم، لكنني لم أعثر على طريقة تحديث صالحة. " \
        "من المرجح أن تصادف مشاكل. " \
        "الرجاء التواصل مع المطور أو طلب الدعم لحل هذه المشكلة."
