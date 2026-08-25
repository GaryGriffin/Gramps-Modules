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

"""MyHeritage Import"""

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

WIKI_PAGE = 'Addon:MyHeritage_DNA'
WARN_MODULE = 'MyHeritageDNA : '

class MyHeritageFinder(tool.Tool,ManagedWindow):
    """
    Import DNA data from My Heritage
    """
    def __init__(self, dbstate, user, options_class, name, callback=None):
        uistate = user.uistate

        tool.Tool.__init__(self, dbstate, options_class, name)

        self.window_name = _('MyHeritage Tool')
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

        MyHeritage_label = Gtk.Label(_('Enter MyHeritage list Filename:'))
        MyHeritage_label.set_valign(Gtk.Align.START)

        self.MyHeritageName = Gtk.FileChooserButton(title="MyHeritage list Filename")

        Segment_label = Gtk.Label(_('Enter MyHeritage Chromosome Segment Filename:'))
        self.SegmentName = Gtk.FileChooserButton(title="MyHeritage Chromosome Segment Filename")

        vbox2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox2.pack_start(MyHeritage_label, False, True, 20)
        vbox2.pack_start(self.MyHeritageName, False, True, 10)

        vbox3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox3.pack_start(Segment_label, False, True, 20)
        vbox3.pack_start(self.SegmentName, False, True, 10)

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

        dnamatch_label = Gtk.Label(_('Import as DNAMatch'))
        self.ImportDNAMatch = Gtk.CheckButton()
        
        vbox8 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox8.pack_start(self.ImportDNAMatch, False, True, 20)
        vbox8.pack_start(dnamatch_label, False, True, 10)
# Add min threshold for importing match data. This is for unknown match
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
        vbox.pack_start(vbox6, False, True, 0)
        vbox.pack_start(vbox8, False, True, 0)
        vbox.pack_start(vbox9, False, True, 0)
        vbox.pack_start(vbox10, False, True, 0)

        button_box = Gtk.HButtonBox()
        button_box.set_layout(Gtk.ButtonBoxStyle.SPREAD)

        get = Gtk.Button(label=_('Import'))
        get.set_tooltip_text(_('Import data from list files'))
        get.connect("clicked", self.__import_myheritage_data)

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

    def __import_myheritage_data(self, obj):

        count = 0
        uistate = self.uistate

        MyHeritageName = self.MyHeritageName.get_filename()
        SegmentName = self.SegmentName.get_filename()
        MatchDNA = self.ImportDNAMatch.get_active()


#
# Read the 2 files and process
#
        if MyHeritageName != None and SegmentName != None:
            self.__process_MyHeritage()
            self.__process_Segment()
            if MatchDNA:
                count = self.__create_match()
#
# Report Results
#
        if uistate:
            if MyHeritageName == None:
                OkDialog(_("MyHeritage DNA Import"),
                        _("No My Heritage list File specified"),
                        parent = uistate.window)
            if SegmentName == None:
                OkDialog(_("MyHeritage DNA Import"),
                         _("No Segment File specified"),
                         parent = uistate.window)
            if MatchDNA:
                if count > 0:
                    OkDialog(_("MyHeritage DNA Import"),
                             _("{} DNAMatches created. \n".format(count)),
                             parent = uistate.window)
                else:
                    OkDialog(_("MyHeritage DNA Import"),
                             _("Nothing Imported from FTdna files."),
                             parent = uistate.window)
        else:
            print("{} DNA data created.".format(count))

    def __create_match(self):
        count = 0
        self.progress = None
# Create DNATest for active person
        active_handle = self.uistate.get_active('Person')
        active_person = self.dbstate.db.get_person_from_handle(active_handle)
        active_dnatest = None
# If Active person already has a DNATest, use that. Otherwise create a new one
        active_test_handles = self.dbstate.db.find_backlink_handles(active_handle, ["DNATest"])
        for class_name_test, active_test_handle in active_test_handles:
            if active_test_handle : 
                active_dnatest = self.dbstate.db.get_dnatest_from_handle(active_test_handle)
                continue
        if not active_dnatest:
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
            self.progress = ProgressMeter(_("MyHeritage DNA Import"),can_cancel = True)
            self.progress.set_pass(_('Please wait, processing segment data...'), mode=1 )
# Build username cache for dedup check
        username_cache = {}
        for handle in self.dbstate.db.get_dnatest_handles():
            Test = self.dbstate.db.get_dnatest_from_handle(handle)
            Kit_ID_Name = Test.get_kit_id()
            Kit_Handle = handle
            username_cache[Kit_ID_Name] = Kit_Handle
        match_cache = []
        for handle in self.dbstate.db.get_dnamatch_handles():
            Match = self.dbstate.db.get_dnamatch_from_handle(handle)
            Subject_Test = Match.get_subject_test_handle()
            Match_Test = Match.get_match_test_handle()
            match_cache.append((Subject_Test,Match_Test))
#            print(" Current Cache : ",Subject_Test,Match_Test)
# Read lines from FF file and process
# "DNA Match ID",
#	Name
# "Estimated relationship",
# "Total cM shared",
# "Percent DNA shared",
# "Number of shared segments",
# "Largest segment (cM)",
        for test_match in self.__FFdata:
            if self.DeDup.get_active() or (test_match[0] not in username_cache):
                username_cache[test_match[0]] = None
                if minThresholdStr != '' and (float(minThresholdStr) < float(test_match[3])):
                    match_dnatest = self.__make_dnatest(test_match)
                    match_dnatest.add_citation(cit.handle)
                    self._add_DNATest(match_dnatest)
                else:
                    continue
            else:	# MyHeritage DNATest exists. Use it
                if username_cache[test_match[0]] :
                	handle = username_cache[test_match[0]]
                	match_dnatest = self.dbstate.db.get_dnatest_from_handle(handle)
                else:
                	continue
# If DNAMatch of subject,match exists, skip processing Match data
#            print("New Entry : ",active_dnatest.get_handle(), match_dnatest.get_handle())
            if (active_dnatest.get_handle(), match_dnatest.get_handle()) in match_cache: continue
            if (match_dnatest.get_handle(), active_dnatest.get_handle()) in match_cache: continue
#
            match_dnamatch = DNAMatch()
            match_dnamatch.set_subject_test_handle(active_dnatest.get_handle())
            match_dnamatch.set_match_test_handle(match_dnatest.get_handle())
            relationShip = PredictedRelationship()
            relationShip.set_description(test_match[2])
            match_dnamatch.add_predicted_relationship(relationShip)
#            match_dnamatch.set_predicted_relationship(test_match[2])
            match_dnamatch.set_shared_cm(float(test_match[3]))
            match_dnamatch.set_percent_shared(float(test_match[4]))
            match_dnamatch.set_segment_count(int(test_match[5]))
            match_dnamatch.set_largest_segment_cm(float(test_match[6]))
            match_dnamatch.add_citation(cit.handle)
            self.__create_segments(test_match[0], match_dnamatch)
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
        match_dnatest.set_account_name(test_match[1])
        match_dnatest.set_kit_id(test_match[0])
        return match_dnatest
    
    def __create_segments(self,match_name, dnamatch):
# File Format for Chromosome Browser
# "DNA Match ID",
# Name,
# "Match name",
# Chromosome,
# "Start Location",
# "End Location",
# "Start RSID",
# "End RSID",
# Centimorgans,
# SNPs
        for seg in self.__Segment :
            if match_name == seg[0] :
                segment = DNASegment()
                segment.set_chromosome(seg[3])
                segment.set_start_bp(int(seg[4]))
                segment.set_end_bp(int(seg[5]))
                segment.set_start_rsid(seg[6])
                segment.set_end_rsid(seg[7])
                segment.set_shared_cm(float(seg[8]))
                segment.set_snp_count(int(seg[9]))
                dnamatch.add_segment(segment)
    
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

    def __process_MyHeritage(self):
        MyHeritageName = self.MyHeritageName.get_filename()
# list File Format for MyHeritage:
# "DNA Match ID",
# Name,
# Age,
# Country,
# "Contact DNA Match",
# "DNA managed by",
# "Contact DNA Manager",
# Status,
# "Estimated relationship",
# "Total cM shared",
# "Percent DNA shared",
# "Number of shared segments",
# "Largest segment (cM)",
# "Review DNA Match page",
# "Has family tree",
# "Number of individuals in the tree",
# "Tree managed by",
# "View tree",
# "Contact tree manager",
# "Number of Smart Matches",
# "Shared Ancestral Surnames",
# "All ancestral surnames",
# Labels,
# "Marked as Favorite",
# Notes,
# "Has Theory of Family Relativity™"
#
# _FFdata order:
# "DNA Match ID",
#	Name
# "Estimated relationship",
# "Total cM shared",
# "Percent DNA shared",
# "Number of shared segments",
# "Largest segment (cM)",
#
#
        self.__FFdata = []
        with open(MyHeritageName, newline='') as file1:
            reader = csv.reader(file1)
            body_line = False
            for row in reader:
                if  body_line:
                    if row[8] : 
                        self.__FFdata.append([row[0],row[1],row[8],row[9],row[10],row[11], row[12]])
                body_line = True
        self.__FFdata.sort()

    def __process_Segment(self):
        SegmentName = self.SegmentName.get_filename()
# File Format for Chromosome Browser
# "DNA Match ID",
# Name,
# "Match name",
# Chromosome,
# "Start Location",
# "End Location",
# "Start RSID",
# "End RSID",
# Centimorgans,
# SNPs
        self.__Segment = []
        with open(SegmentName, newline='') as file2:
            reader = csv.reader(file2)
            body_line = False
            for row in reader:
                if body_line:
                    if row : self.__Segment.append(row)
                body_line = True
        self.__Segment.sort()

    def __create_source_citation(self):
        cit_source = Source()
        cit_source.set_title("My Heritage DNA")
        cit_source.set_abbreviation("MyHeritage")
        cit_source.set_author("My Heritage")
        cit_source.set_publication_info("https://www.MyHeritage.com")
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

class MyHeritageOptions(tool.ToolOptions):
    """
    Defines options and provides handling interface.
    """
    def __init__(self, name, person_id=None):
        """ Initialize the options class """
        tool.ToolOptions.__init__(self, name, person_id)
