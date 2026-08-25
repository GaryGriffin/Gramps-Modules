#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2024-2026       Gary Griffin
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

"""FTdna Import"""

#------------------------------------------------------------------------
#
# GNOME/GTK modules
#
#------------------------------------------------------------------------
from gi.repository import Gtk
from gi.repository import GObject

#------------------------------------------------------------------------
#
# Gramps modules
#
#------------------------------------------------------------------------

from gramps.gui.plug import tool
from gramps.gen.display.name import displayer as _nd
from gramps.gen.plug import Gramplet
from gramps.gen.lib import DNATest, DNAMatch, DNASegment, PredictedRelationship
from gramps.gui.managedwindow import ManagedWindow
from gramps.gen.db import DbTxn
from gramps.gen.lib import Attribute, Note, Citation, PersonRef, NoteType, Source
from gramps.gui.dialog import OkDialog
from gramps.gui.utils import ProgressMeter
from gramps.gui.display import display_help, display_url
import csv
import re
# -------------------------------------------------------------------------
# Internationalization
# -------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

#-------------------------------------------------------------------------
#
# Constants
#
#-------------------------------------------------------------------------

WIKI_PAGE = 'Addon:FamilyTree_DNA'
WARN_MODULE = 'FamilyTreeDNA : '

class FamilyFinder(tool.Tool,ManagedWindow):
    """
    Import DNA data from Family Tree
    """
    def __init__(self, dbstate, user, options_class, name, callback=None):
        uistate = user.uistate

        tool.Tool.__init__(self, dbstate, options_class, name)

        self.window_name = _('Family Finder Tool')
        ManagedWindow.__init__(self, uistate, [], self.__class__)

        self.dbstate = dbstate
        self.db = dbstate.db
        """
        Initialise the gramplet.
        """

        window = Gtk.Window()

        root = self.__create_gui()
        root.show_all()

        window.add(root)
        window.set_size_request(500, 300)
        window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_window(window, None, self.window_name)
        self.show()

    def __create_gui(self):
        """
        Create and display the GUI components of the gramplet.
        """
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        FamilyFinder_label = Gtk.Label(_('Enter FTDNA Family Finder Filename:'))
        FamilyFinder_label.set_valign(Gtk.Align.START)

        self.FamilyFinderName = Gtk.FileChooserButton(title="FTDNA Family Finder Filename")

        Segment_label = Gtk.Label(_('Enter FTDNA Chromosome Segment Filename:'))
        self.SegmentName = Gtk.FileChooserButton(title="FTDNA Chromosome Segment Filename")

        Haplo_label = Gtk.Label(_('Import Haplogroups as Attribute'))
        self.ImportHaplo = Gtk.CheckButton()


        vbox2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox2.pack_start(FamilyFinder_label, False, True, 20)
        vbox2.pack_start(self.FamilyFinderName, False, True, 10)

        vbox3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox3.pack_start(Segment_label, False, True, 20)
        vbox3.pack_start(self.SegmentName, False, True, 10)

        vbox4 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox4.pack_start(self.ImportHaplo, False, True, 20)
        vbox4.pack_start(Haplo_label, False, True, 10)

        SearchString_label = Gtk.Label(_('FTDNA Note string :'))
        self.NoteString = Gtk.Entry()
        text="GRAMPSID="
        self.NoteString.set_text(text)

        vbox5 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox5.pack_start(SearchString_label, False, True, 20)
        vbox5.pack_start(self.NoteString, False, True, 10)

        CitationString_label = Gtk.Label(_('Shared Citation ID :'))
        self.CitationID = Gtk.Entry()

        vbox6 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox6.pack_start(CitationString_label, False, True, 20)
        vbox6.pack_start(self.CitationID, False, True, 10)

        active_handle = self.uistate.get_active('Person')
        if active_handle == None:
            return
        try:
            active = self.dbstate.db.get_person_from_handle(active_handle)
        except:
            return
        self.__active = active
        self.Active_label = Gtk.Label(_('Active Person : ') + _nd.display(active))
# Add checkbox for import type
        assoc_note_label = Gtk.Label(_('Import as Association Note'))
        self.ImportAssocNote = Gtk.CheckButton()

        vbox7 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox7.pack_start(self.ImportAssocNote, False, True, 20)
        vbox7.pack_start(assoc_note_label, False, True, 10)

        dnamatch_label = Gtk.Label(_('Import as DNAMatch'))
        self.ImportDNAMatch = Gtk.CheckButton()
        
        vbox8 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox8.pack_start(self.ImportDNAMatch, False, True, 20)
        vbox8.pack_start(dnamatch_label, False, True, 10)
# Add min threshold for importing match data when no GRAMPSID is included. This is for unknown match
        min_threshold_label = Gtk.Label (_('Min cM for DNA Match import : '))
        self.MinThresholdImport = Gtk.Entry()
        vbox9 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox9.pack_start(min_threshold_label, False, True, 10)
        vbox9.pack_start(self.MinThresholdImport, False, True, 5)
# Add de-dup checkbox
        dedup_label = Gtk.Label(_('Include duplicate matches'))
        self.DeDup = Gtk.CheckButton()
        vbox10 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox10.pack_start(self.DeDup, False, True, 20)
        vbox10.pack_start(dedup_label, False, True, 10)
# End checkbox for import type
        vbox.pack_start(self.Active_label, False, True, 0)
        vbox.pack_start(vbox2, False, True, 0)
        vbox.pack_start(vbox3, False, True, 0)
        
        vbox.pack_start(vbox5, False, True, 0)
        vbox.pack_start(vbox6, False, True, 0)
        vbox.pack_start(vbox7, False, True, 0)
        vbox.pack_start(vbox4, False, True, 0)
        vbox.pack_start(vbox8, False, True, 0)
        vbox.pack_start(vbox9, False, True, 0)
        vbox.pack_start(vbox10, False, True, 0)

        button_box = Gtk.HButtonBox()
        button_box.set_layout(Gtk.ButtonBoxStyle.SPREAD)

        get = Gtk.Button(label=_('Import'))
        get.set_tooltip_text(_('Import data from Family Finder files'))
        get.connect("clicked", self.__import_ftdna_data)

        close = Gtk.Button(_('Close'))
        close.set_tooltip_text(_('Close the Family Finder Tool'))
        close.connect('clicked', self.close)

        help = Gtk.Button(_('Help'))
        help.set_tooltip_text(_('Read Help manual'))
        help.connect('clicked', self.__web_help)

        button_box.add(help)
        button_box.add(get)
        button_box.add(close)
        button_box.set_child_non_homogeneous(help, True)
        vbox.pack_start(button_box, False, True, 0)

        return vbox

    def __import_ftdna_data(self, obj):

        count = 0
        self.msg = [0,0,0,0,0]
        warn_str = ""
        haplo_count = 0
        uistate = self.uistate

        FamilyFinderName = self.FamilyFinderName.get_filename()
        SegmentName = self.SegmentName.get_filename()
        ImportHaplo = self.ImportHaplo.get_active()
        AssocNote = self.ImportAssocNote.get_active()
        MatchDNA = self.ImportDNAMatch.get_active()
        self.note_string = self.NoteString.get_text()

#
# Read the 2 files and process
#
        if FamilyFinderName != None and SegmentName != None:
            self.__process_FamilyFinder()
            self.__process_Segment()
            if ImportHaplo : haplo_count = self.__process_haplogroup()
            if AssocNote:
                count = self.__add_associations()
            if MatchDNA:
                count = self.__create_match()
#
# Summarize Issues
#
        if self.msg[0] :
            warn_str += str(self.msg[0])+" GrampsID error extracting haplogroup" + "\n"
        if self.msg[1] :
            warn_str += str(self.msg[1])+" Haplogroup already set"  + "\n"
        if self.msg[2] :
            warn_str += str(self.msg[2])+" DNA Association already exists" + "\n"
        if self.msg[3] :
            warn_str += str(self.msg[3]) + " GrampsID error extracting segment info" + "\n"
        if self.msg[4] :
            warn_str += " Invalid Citation ID - generated Citation"
#
# Report Results
#
        if uistate:
            if FamilyFinderName == None:
                OkDialog(_("FamilyTree DNA Import"),
                        _("No Family Finder File specified"),
                        parent = uistate.window)
            if SegmentName == None:
                OkDialog(_("FamilyTree DNA Import"),
                         _("No Segment File specified"),
                         parent = uistate.window)
            if AssocNote:
                if count + haplo_count > 0:
                    OkDialog(_("FamilyTree DNA Import"),
                             _("{} Associations with DNA data created. {} haplogroup Attributes created \n".format(count, haplo_count))+warn_str,
                             parent = uistate.window)
                else:
                    OkDialog(_("FamilyTree DNA Import"),
                             _("Nothing Imported from FTdna files. No haplogroup Attributes created."),
                             parent = uistate.window)
            if MatchDNA:
                if count > 0:
                    OkDialog(_("FamilyTree DNA Import"),
                             _("{} DNAMatches created. {} haplogroup Attributes created \n".format(count, haplo_count))+warn_str,
                             parent = uistate.window)
                else:
                    OkDialog(_("FamilyTree DNA Import"),
                             _("Nothing Imported from FTdna files."),
                             parent = uistate.window)
        else:
            print("{} DNA data created. {} haplogroup Attributes created".format(count, haplo_count))

    def __create_match(self):
        count = 0
        self.progress = None
# Create DNATest for active person
        active_handle = self.uistate.get_active('Person')
        active_person = self.dbstate.db.get_person_from_handle(active_handle)
        active_dnatest=DNATest()
        active_dnatest.set_account_name(_nd.display(active_person))
        active_dnatest.set_person_handle(active_handle)
        active_dnatest.set_test_type("Autosomal")
        self._add_DNATest(active_dnatest)
# Citation for DNATest and DNAMatch
        citID = self.CitationID.get_text()
        cit = None
        if citID :
            cit = self.dbstate.db.get_citation_from_gramps_id(citID)
        if not cit :
            cit = self.__create_source_citation()
#
        minThresholdStr = self.MinThresholdImport.get_text()
        if minThresholdStr != '':
            self.progress = ProgressMeter(_("FamilyTree DNA Import"),can_cancel = True)
            self.progress.set_pass(_('Please wait, processing segment data...'), mode=1 )
# Build username cache for dedup check
        username_cache = []
        for handle in self.dbstate.db.get_dnatest_handles():
            Subject = self.dbstate.db.get_dnatest_from_handle(handle)
            Subject_Account_Name = Subject.get_account_name()
            username_cache.append(Subject_Account_Name)
# Read lines from FF file and process
        for test_match in self.__FFdata:
            assoc = self.__find_match_name(test_match)
            if self.DeDup.get_active() or (test_match[8] not in username_cache):
                username_cache.append(test_match[8])
                if assoc:
                    match_dnatest = self.__make_dnatest(test_match)
                    match_dnatest.set_person_handle(assoc.get_handle())
                elif minThresholdStr != '' and (float(minThresholdStr) < float(test_match[4])):
                    match_dnatest = self.__make_dnatest(test_match)
                else:
                    continue
            else:
                continue
            match_dnatest.add_citation(cit.handle)
            self._add_DNATest(match_dnatest)
            match_dnamatch = DNAMatch()
            match_dnamatch.set_subject_test_handle(active_dnatest.get_handle())
            match_dnamatch.set_match_test_handle(match_dnatest.get_handle())
            match_dnamatch.set_shared_cm(float(test_match[4]))
            match_dnamatch.set_largest_segment_cm(float(test_match[5]))
            match_dnamatch.add_citation(cit.handle)
            if not assoc:
                relationShip = PredictedRelationship()
                relationShip.set_description(test_match[7])
                match_dnamatch.add_predicted_relationship(relationShip)
#                match_dnamatch.set_predicted_relationship(test_match[7])
            self.__create_segments(test_match[0],match_dnamatch, test_match[9])
            self._add_DNAMatch(match_dnamatch)
            count += 1
            if self.progress:
                if count %10 == 0: self.progress.set_header("%d DNA Tests loaded" % count)
                self.progress.step()
                if self.progress.get_cancelled():
                    break
        if self.progress: self.progress.close()
        return count

    def __make_dnatest(self,test_match):
        match_dnatest = DNATest()
        match_dnatest.set_test_type("Autosomal")
        match_dnatest.set_account_name(test_match[8])
        if test_match[6] == "No": match_dnatest.set_provider("FTDNA")
        match_dnatest.set_y_haplogroup(test_match[1])
        match_dnatest.set_mt_haplogroup(test_match[2])
        return match_dnatest
    
    def __create_segments(self,match_name,dnamatch, bucket):
        seg_count = 0
        for seg in self.__Segment :
            if match_name == seg[0] :
                segment = DNASegment()
                segment.set_chromosome(seg[1])
                segment.set_start_bp(int(seg[2]))
                segment.set_end_bp(int(seg[3]))
                segment.set_shared_cm(float(seg[4]))
                segment.set_snp_count(int(seg[5]))
                dnamatch.add_segment(segment)
                if bucket == "Maternal": 
                    segment.set_origin(2)
                elif bucket == "Paternal":
                    segment.set_origin(3)
                seg_count += 1
        dnamatch.set_segment_count(seg_count)

    def __find_match_name(self, match):
        substring = match[3].split()
        start_pos = len(self.note_string)
        stop_pos = len(match[3])
        person = None
        gid = None
        for i in substring :
            if self.note_string in i :
                start_pos = i.find(self.note_string) + len(self.note_string)
                stop_pos = len(i)
                gid = i[start_pos:stop_pos]
        if gid: person = self.dbstate.db.get_person_from_gramps_id(gid)
        return person
    
    def _add_DNATest(self,obj):
        if not obj.handle:
            with DbTxn(
                _("Add DNA Test (%s)") % obj.get_gramps_id(), self.db
            ) as trans:
                self.db.add_dnatest(obj, trans)
        else:
            with DbTxn(
                _("Edit DNA Test (%s)") % obj.get_gramps_id(), self.db
            ) as trans:
                if not obj.get_gramps_id():
                    obj.set_gramps_id(self.db.find_next_dnatest_gramps_id())
                self.db.commit_dnatest(obj, trans)

    def _add_DNAMatch(self,obj):
        if not obj.handle:
            with DbTxn(
                _("Add DNA Match (%s)") % obj.get_gramps_id(), self.db
            ) as trans:
                self.db.add_dnamatch(obj, trans)
        else:
            with DbTxn(
                _("Edit DNA Match (%s)") % obj.get_gramps_id(), self.db
            ) as trans:
                if not obj.get_gramps_id():
                    obj.set_gramps_id(self.db.find_next_dnamatch_gramps_id())
                self.db.commit_dnamatch(obj, trans)

    def __process_FamilyFinder(self):
        FamilyFinderName = self.FamilyFinderName.get_filename()
# File Format for Family Finder:
#	Full Name,
#	First Name,
#	Middle Name,
#	Last Name,
#	Match Date,
#	Relationship Range,
#	Shared DNA,
#	Longest Block,
#	Linked Relationship,
#	Ancestral Surnames,
#	Y-DNA Haplogroup,
#	mtDNA Haplogroup,
#	Notes (where GRAMPSID is stored for matching),
#	Matching Bucket,
#	X-Match,
#	Autosomal Transfer
# _FFdata order:
#	Name
#	Y-DNA Haplogroup
#	mtDNA Haplogroup
#	Notes (where GRAMPSID is stored for matching)
#	Shared DNA
#	Longest Block
#	Autosomal Transfer
#	Relationship Range
#   Full Name
#.  Matching Bucket
#
        self.__FFdata = []
        with open(FamilyFinderName, newline='') as file1:
            reader = csv.reader(file1)
            body_line = False
            for row in reader:
                if  body_line:
                    new_row = [s.strip() for s in row]
                    concat_name = ' '.join([new_row[1],new_row[2],new_row[3]])
                    new_name = re.sub("\\s{2,}", ' ', concat_name)
                    self.__FFdata.append([new_name.strip(),new_row[10],new_row[11],new_row[12],new_row[6],new_row[7], new_row[15], new_row[5], new_row[0], new_row[13]])
                body_line = True
        self.__FFdata.sort()

    def __process_Segment(self):
        SegmentName = self.SegmentName.get_filename()
# File Format for Chromosome Browser
#	Match Name,
#	Chromosome,
#	Start Location,
#	End Location,
#	Centimorgans,
#	Matching SNPs
        self.__Segment = []
        with open(SegmentName, newline='') as file2:
            reader = csv.reader(file2)
            body_line = False
            for row in reader:
                if body_line:
                    if row : 
                        new_row = [s.strip() for s in row]
                        concat_name = new_row[0].strip()
                        new_name = re.sub("\\s{2,}", ' ', concat_name)
                        self.__Segment.append((new_name, new_row[1], new_row[2], new_row[3], new_row[4], new_row[5]))
                body_line = True
        self.__Segment.sort()

    def __process_haplogroup(self) :
        mt_count = 0
        y_count = 0
        for match in self.__FFdata:
            person = self.__find_match_name(match)
            if person :
                if match[1] :
                    y_count += self.__process_specific_haplogroup(person, match[1],"Y-DNA")
                if match[2] :
                    mt_count += self.__process_specific_haplogroup(person, match[2],"mtDNA")
        count = mt_count + y_count
        return count

    def __process_specific_haplogroup(self,person,attr_val, attr_type) :
        count = 0
        att = Attribute()
        attr_list = person.get_attribute_list()
        attr_found = False
        for i in attr_list :
            if attr_type == i.get_type() : attr_found = True
        if attr_found :
            print(WARN_MODULE, "{} attribute already present - not adding to {}".format(attr_type, _nd.display(person)))
            self.msg[1] += 1
        else:
            att.set_type(attr_type)
            att.set_value(attr_val)
            with DbTxn (_('Add %s haplogroup attribute' ) % _nd.display(person), self.dbstate.db) as self.trans:
                person.add_attribute(att)
                self.dbstate.db.commit_person(person, self.trans)
            count += 1
        return count

    def __add_associations(self) :
        count = 0
        make_cit = True
        rel = "DNA"
        active_handle = self.uistate.get_active('Person')
        active_person = self.dbstate.db.get_person_from_handle(active_handle)
        for match in self.__FFdata :
            substring = match[3].split()
            start_pos = len(self.note_string)
            stop_pos = len(match[3])
            match_person = None
            gid = None
            for i in substring :
                if self.note_string in i :
                    start_pos = i.find(self.note_string) + len(self.note_string)
                    stop_pos = len(i)
                    gid = i[start_pos:stop_pos]
            if gid: match_person = self.dbstate.db.get_person_from_gramps_id(gid)
            if match_person :
                match_handle = match_person.get_handle()
                note_txt = ""
                new_match = True
                assoc_needed = True
                for seg in self.__Segment :
                    if match[0] == seg[0] :
                        need_note = True
                        if new_match :
                            update_needed = True
                            for existing_assoc in active_person.get_person_ref_list() :
                                if existing_assoc.get_relation() == rel:
                                    existing_person = self.dbstate.db.get_person_from_handle(existing_assoc.ref)
                                    if match_handle == existing_person.get_handle() :
                                        update_needed = False
                                        need_note = False
                                        note_txt = ""
                            if update_needed :
                                personRef = PersonRef()
                                personRef.set_reference_handle(match_handle)
                                personRef.set_relation(rel)
                                with DbTxn (_('Add %s DNA Association' ) % _nd.display(active_person), self.dbstate.db) as self.trans:
                                    active_person.add_person_ref(personRef)
                                    self.dbstate.db.commit_person(active_person, self.trans)
                                new_match = False
                                count += 1
                            else:
                                if assoc_needed :
                                    print(WARN_MODULE, "DNA Association already exists for {} to {}".format(_nd.display(active_person), _nd.display(match_person)))
                                    assoc_needed = False
                                need_note = False
                                note_txt = ""
                        if need_note:
                            note_txt += seg[1]+","+seg[2]+","+seg[3]+","+seg[4]+","+seg[5]+"\n"
                if note_txt :
                    new_note = Note()
                    new_note.set(note_txt)
                    new_note.set_type(NoteType.ASSOCIATION)
                    with DbTxn (_('Create Note for %s DNA Association' ) % _nd.display(match_person), self.dbstate.db) as self.trans:
                        self.dbstate.db.add_note(new_note, self.trans)
                    with DbTxn (_('Add Note to %s DNA Association' ) % _nd.display(match_person), self.dbstate.db) as self.trans:
                        personRef.add_note(new_note.handle)
                        self.dbstate.db.commit_person(active_person, self.trans)
                    if make_cit :
                        citID = self.CitationID.get_text()
                        cit = None
                        if citID :
                            cit = self.dbstate.db.get_citation_from_gramps_id(citID)
                            if not cit :
                                self.msg[4] = 1
                        if not cit :
                            cit = self.__create_source_citation()
                    make_cit = False
                    with DbTxn (_('Add Citation to %s DNA Association' ) % _nd.display(match_person), self.dbstate.db) as self.trans:
                        personRef.add_citation(cit.handle)
                        self.dbstate.db.commit_person(active_person, self.trans)
        return count

    def __create_source_citation(self):
        cit_source = Source()
        cit_source.set_title("Family Tree DNA")
        cit_source.set_abbreviation("FTDNA")
        cit_source.set_author("Family Tree")
        cit_source.set_publication_info("https://www.familytreedna.com")
        with DbTxn (_('Create Source Citation for DNA Data' ), self.dbstate.db) as self.trans:
           self.dbstate.db.add_source(cit_source, self.trans)
           self.dbstate.db.commit_source(cit_source, self.trans)
        cit = Citation()
        cit.set_reference_handle(cit_source.handle)
        with DbTxn (_('Create Citation for DNA Data' ), self.dbstate.db) as self.trans:
           self.dbstate.db.add_citation(cit, self.trans)
           self.dbstate.db.commit_citation(cit, self.trans)
        return cit
    
    def __web_help(self, obj):
        display_help(WIKI_PAGE)

    def main(self):
        pass

class FamilyFinderOptions(tool.ToolOptions):
    """
    Defines options and provides handling interface.
    """
    def __init__(self, name, person_id=None):
        """ Initialize the options class """
        tool.ToolOptions.__init__(self, name, person_id)
