#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2026  Gary Griffin
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

"""
ConvertDNA Gramplet
This Gramplet converts Notes in Associations to DNATest and DNAMatch objects
"""
#-------------------------------------------------------------------------
#
# Gtk modules
#
#-------------------------------------------------------------------------


#------------------------------------------------------------------------
#
# Gramps modules
#
#------------------------------------------------------------------------

from gramps.gui.plug import tool
from gramps.gen.lib import DNATest, DNAMatch, DNASegment
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.db import DbTxn
from gramps.gui.managedwindow import ManagedWindow

from gramps.gen.display.name import displayer as _nd

import re
import csv
import os
_ = glocale.translation.gettext

class ConvertDNA(ManagedWindow):
    def __init__(self, dbstate, user, options_class, name, callback=None):
        uistate = user.uistate
        self.dbstate = dbstate
        self.uistate = uistate # ADDED
        self.db = dbstate.db
        active_handle = self.uistate.get_active("Person") # ADDED
#        active = self.db.get_person_from_gramps_id("I00001")
#        active_handle = active.get_handle()
        association_string = "DNA"
        include_citation_notes = False
        if active_handle:
            active = self.db.get_person_from_handle(active_handle)
# Create active DNATest as autosomal
            active_dnatest=DNATest()
            active_dnatest.set_person_handle(active_handle)
            active_dnatest.set_test_type("Autosomal")
            self._add_DNATest(active_dnatest)
            for assoc in active.get_person_ref_list():
                if assoc.get_relation() == association_string:
                    associate = self.db.get_person_from_handle(assoc.ref)
#Create associate DNATest as autosomal
                    match_dnatest = DNATest()
                    match_dnatest.set_person_handle(assoc.ref)
                    match_dnatest.set_test_type("Autosomal")
    # Look for Provider in Source Citation. Do not include GEDmatch as testing source is still unknown
                    provider = "Unknown"
                    for citation_handle in assoc.get_citation_list() :
                        citation = self.db.get_citation_from_handle(citation_handle)
                        source_handle = citation.get_reference_handle()
                        source = self.db.get_source_from_handle(source_handle)
                        try:
                            source_title = source.get_title()
                        except:
                            continue
                        if "Ancestry" in source_title:
                            provider = "AncestryDNA"
                        elif "Heritage" in source_title:
                            provider = "MyHeritage"
                        elif "FTDNA" in source_title:
                            provider = "FTDNA"
                        elif "Family Tree" in source_title:
                            provider = "FTDNA"
                        elif "Living" in source_title:
                            provider = "LivingDNA"
                        elif "23" in source_title:
                            provider = "23andMe"
                    match_dnatest.set_provider(provider)
                    self._add_DNATest(match_dnatest)
                # Get Notes attached to Association
                    for handle in assoc.get_note_list():
                        note = self.db.get_note_from_handle(handle)
#Create DNAMatch
                        dnamatch = DNAMatch()
                        segment_list = []
                        dnamatch.set_segment_list(segment_list)                      
                        segment_list = dnamatch.get_segment_list()
                        segment_count = 0
                        largest_cm = 0
                        shared_cm = 0
                        for line in note.get().split('\n'):
#Create DNAMatch Segment
                            segment = self._create_segment(line)
                            if segment:
                                segment_count += 1
                                largest_cm = max(largest_cm, segment.get_shared_cm())
                                shared_cm += segment.get_shared_cm()
                                dnamatch.add_segment(segment)
                            else: # check for single number in line (Ancestry shared cM case)
                                field = line.split(',')
                                if len(field) == 1:
                                    try:
                                        shared_cm = float(field[0])
                                        match_dnatest.set_provider("AncestryDNA")
                                        self._add_DNATest(match_dnatest)
                                    except:
                                        continue
                        dnamatch.set_shared_cm(shared_cm)
                        dnamatch.set_subject_test_handle(active_dnatest.get_handle())
                        dnamatch.set_match_test_handle(match_dnatest.get_handle())
                        dnamatch.set_segment_count(segment_count)
                        dnamatch.set_largest_segment_cm(largest_cm)
                        for citation_handle in assoc.get_citation_list() :
                            dnamatch.add_citation(citation_handle)
                        self._add_DNAMatch(dnamatch)
                # Get Notes attached to Citation which is attached to the Association
                    if include_citation_notes :
                        for citation_handle in assoc.get_citation_list():
                            citation = self.db.get_citation_from_handle(citation_handle)
#Create DNAMatch
                            dnamatch = DNAMatch()
                            segment_list = []
                            dnamatch.set_segment_list(segment_list)
                            segment_list = dnamatch.get_segment_list()
                            segment_count = 0
                            largest_cm = 0
                            for handle in citation.get_note_list():
                                note = self.db.get_note_from_handle(handle)
                                for line in note.get().split('\n'):
#Create DNAMatch Segment
                                    segment = self._create_segment(line)
                                    if segment:
                                        segment_count += 1
                                        largest_cm = max(largest_cm, segment.get_shared_cm())
                                        shared_cm += segment.get_shared_cm()
                                        dnamatch.add_segment(segment)
                                    else: # check for single number in line (Ancestry shared cM case)
                                        field = line.split(',')
                                        if len(field) == 1:
                                            try:
                                                shared_cm = float(field[0])
                                            except:
                                                shared_cm = 0
                                            match_dnatest.set_provider("AncestryDNA")
                                            self._add_DNATest(match_dnatest)
                                dnamatch.set_shared_cm(shared_cm)
                                dnamatch.set_subject_test_handle(active_dnatest.get_handle())
                                dnamatch.set_match_test_handle(match_dnatest.get_handle())
                                dnamatch.set_segment_count(segment_count)
                                dnamatch.set_largest_segment_cm(largest_cm)
                                self._add_DNAMatch(dnamatch)
    def _add_DNATest(self,obj):
        if not obj.handle:
            with DbTxn(
                _("Add DNA Test (%s)") % obj.get_gramps_id(), self.db
            ) as trans:
                self.db.add_dnatest(obj, trans)
        else:
            if True:
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
            if self.data_has_changed():
                with DbTxn(
                    _("Edit DNA Match (%s)") % obj.get_gramps_id(), self.db
                ) as trans:
                    if not obj.get_gramps_id():
                        obj.set_gramps_id(self.db.find_next_dnamatch_gramps_id())
                    self.db.commit_dnamatch(obj, trans)
    def _create_segment(self,line):
        if "\t" in line:
# Tabs are the field separators. Now determine THOUSEP and RADIXCHAR. Use Field 2 (Stop Pos) to see if there are THOUSEP there. Use Field 3 (SNPs) to see if there is a radixchar
            field = line.split('\t')
            if len(field) > 3:
                if "," in field[2]:
                    line = line.replace(",", "")
                elif "." in field[2]:
                    line = line.replace(".", "")
                if "," in field[3]:
                    line = line.replace(",", ".")
            else:
                print("Skipping: ",line)
            line = line.replace("\t", ",")
# If Tab is not the field separator, then comma is. And point is the radixchar.
        field = line.split(',')
        if len(field) < 4:
            return False
        chromo = field[0].strip()
        start = get_base(field[1])
        stop = get_base(field[2])
        try:
            cms = float(field[3])
        except:
            return False
        try:
            snp = int(field[4])
        except:
            snp = 0
        segment = DNASegment()
        segment.set_chromosome(chromo)
        segment.set_start_bp(start)
        segment.set_end_bp(stop)
        segment.set_shared_cm(cms)
        segment.set_snp_count(snp)
        return segment

def get_base(num):
    try:
        return int(num)
    except:
        try:
            return int(float(num) * 1000000)
        except:
            return 0
            
#------------------------------------------------------------------------
#
# ConvertDNAOptions
#
#------------------------------------------------------------------------
class ConvertDNAOptions(tool.ToolOptions):
    """
    Defines options and provides handling interface.
    """
    def __init__(self, name, person_id=None):
        """ Initialize the options class """
        tool.ToolOptions.__init__(self, name, person_id)