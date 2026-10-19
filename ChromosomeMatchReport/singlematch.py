# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2026      Gary Griffin <genealogy@garygriffin.net>
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

"""Single Chromosome Match Report"""
#
#
#------------------------------------------------------------------------
#
# standard python modules
#
#------------------------------------------------------------------------
import math
import csv
import io
import time
from operator import itemgetter

#------------------------------------------------------------------------
#
# Gramps modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.errors import ReportError
from gramps.gen.lib import (Person, Event, Media, Family, EventType)
from gramps.gen.plug.docgen import (IndexMark, FontStyle, ParagraphStyle,
                                    TableStyle, TableCellStyle,
                                    FONT_SANS_SERIF, FONT_SERIF,
                                    INDEX_TYPE_TOC, PARA_ALIGN_CENTER, PARA_ALIGN_RIGHT)
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import utils
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.menu import (EnumeratedListOption, StringOption, NumberOption, PersonOption, BooleanOption)
from gramps.gen.lib import DNATest, DNAMatch, DNASegment
from gramps.gen.plug.report import stdoptions
from gramps.gen.proxy import CacheProxyDb
from gramps.gen.relationship import get_relationship_calculator

from gramps.gen.const import (PROGRAM_NAME, VERSION)

#------------------------------------------------------------------------
#
# Constants
#
#------------------------------------------------------------------------
EMPTY_ENTRY = "_____________"
#
# List of output formats
#
STYLE_ENTRY = 'Table format','CSV format'
CHROMO_ENTRY = '1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18','19','20','21','22','X', 'All'
HEADERS = ['Match ID', 'Person ID', 'Rel', 'Person', 'Start cM', 'End cM']

#------------------------------------------------------------------------
#
# SingleMatchReport. This class much match the reference in the .gpr.py file
#
#------------------------------------------------------------------------


class SingleMatchReport(Report):
    def __init__(self, database, options_class, user):

        Report.__init__(self, database, options_class, user)
        self._user = user
        self._db = database
        menu = options_class.menu
        mgobn = lambda name:options_class.menu.get_option_by_name(name).get_value()
#
# Initialize the user controls
#
        self.style = mgobn('style')
        self.titletext = mgobn('titletext')
        pid = mgobn('pid')
        self.__min_cm = mgobn('min_cm')
        self.__max_cm = mgobn('max_cm')
        self.__chromo = mgobn("chromosome")
        self.center_person = self.database.get_person_from_gramps_id(pid)
        if self.center_person is None:
            raise ReportError(_("Person %s is not in the Database") % pid)
        self.database = CacheProxyDb(self.database)
        self.relationship = get_relationship_calculator(glocale)
#
# Overarrching Report writer. 
#
    def write_report(self):
        if self.__chromo == "All":
            for chromo in CHROMO_ENTRY[:-1]:
                self.__chromosome = chromo
                self.__write_single_report()
                self.doc.page_break()
        else:
            self.__chromosome = self.__chromo
            self.__write_single_report()

    def __write_single_report(self):
        reportRows = self.__generate_rows()
        if self.style == STYLE_ENTRY[0]:
            self.__write_report_table(reportRows)
        if self.style == STYLE_ENTRY[1]:
            self.__write_report_csv(reportRows)

    def __write_report_table(self,reportRowsSorted):
        self.doc.start_paragraph("Single-Attribute-Title")
        title = _("Chromosome Report")
        mark = IndexMark(title, INDEX_TYPE_TOC,1)
        self.doc.write_text(_(self.titletext),mark)
        self.doc.end_paragraph()
# Add Chromosome subtitle
        self.doc.start_paragraph("Single-Attribute-SubTitle")
        subtitle = _("Chromosome ") + self.__chromosome
        mark = IndexMark(title, INDEX_TYPE_TOC,1)
        self.doc.write_text(_(subtitle),mark)
        self.doc.end_paragraph()
# Headers
        self.doc.start_table('Attributes','Single-Attribute-Table')
        self.doc.start_row()
        for i in range(len(HEADERS)):
            self.doc.start_cell('Single-Attribute-TableCell')
            if i < 4:
                self.doc.start_paragraph('Single-Attribute-Normal-Bold')
            else:
                self.doc.start_paragraph('Single-Attribute-Normal-Bold-Right')
            self.doc.write_text(_(HEADERS[i]))
            self.doc.end_paragraph()
            self.doc.end_cell()
        self.doc.end_row()
# ITERATE ROW HERE
        for reportRow in reportRowsSorted :
            self.doc.start_row()
            for i in range(len(HEADERS)): # Change from reportRow to HEADERS to avoid printing chromosome number
                self.doc.start_cell('Single-Attribute-TableCell')
                if i < 4: 
                    self.doc.start_paragraph('Single-Attribute-Normal')
                else:
                    self.doc.start_paragraph('Single-Attribute-Normal-Right')
                self.doc.write_text(str(reportRow[i]))
                self.doc.end_paragraph()
                self.doc.end_cell()
            self.doc.end_row()
        self.doc.end_table()

    def __write_report_csv(self, reportRowsSorted):
        output = io.StringIO()
        writer = csv.writer(output)
#        writer.writerow(HEADERS)
# ITERATE ROW HERE
        for reportRow in reportRowsSorted :
            writer.writerow(reportRow)
        self.doc.start_paragraph('Single-Attribute-Normal')
        self.doc.write_text(output.getvalue())
        self.doc.end_paragraph()

    def __generate_rows(self) :
        reportRows = []
        active_handle = self.center_person.get_handle()
        active_test_handles = self._db.find_backlink_handles(active_handle, ["DNATest"])
        for class_name_test, active_test_handle in active_test_handles:
            if active_test_handle : 
                active_dnatest = self._db.get_dnatest_from_handle(active_test_handle)
                active_match_handles = self._db.find_backlink_handles(active_test_handle, ["DNAMatch"])
                for class_name_match, active_match_handle in active_match_handles:
                    if active_match_handle :
                        active_match = self._db.get_dnamatch_from_handle(active_match_handle)
                        shared_cM = active_match.get_shared_cm()
                        if shared_cM < self.__min_cm : continue
                        if shared_cM > self.__max_cm : continue
                        
                        Subject_Test_handle = active_match.get_subject_test_handle()
                        Match_Test_handle = active_match.get_match_test_handle()
                        if active_test_handle == Subject_Test_handle : 
                            other_handle = Match_Test_handle
                        else:
                            other_handle = Subject_Test_handle
                        person_id=""
                        rel=""
                        matching_test = self._db.get_dnatest_from_handle(other_handle)
                        person_name = matching_test.get_account_name()
                        person_handle = matching_test.get_person_handle()
                        if person_handle: 
                            Other_Person = self._db.get_person_from_handle(person_handle)
                            person_id = Other_Person.get_gramps_id()
                            data, msg = self.relationship.get_relationship_distance_new(self._db,self.center_person,Other_Person,False, True, True)
                            if data[0][0] <= 0: 
                                rel="Unknown"
                            elif data[0][0] == 1:
                                rel="Parent/Child"
                            else: 
                                rel = data[0][2] + " / " + data[0][4]
                        for seg in active_match.get_segment_list() :
                            chromosome = seg.get_chromosome()
                            if chromosome != self.__chromosome: continue
                            match_id = active_match.get_gramps_id()
                            start_cM = seg.get_start_bp()
                            end_cM = seg.get_end_bp()
                            reportRows.append((match_id, person_id, rel, person_name, start_cM, end_cM, chromosome))

        reportRowsSorted = sorted (reportRows, reverse = False, key=itemgetter(4,5))
        return reportRowsSorted

#------------------------------------------------------------------------
#
# Single Report Options - this class must be the same as specified in the .gpr.py file
#
#------------------------------------------------------------------------
class SingleMatchReportOptions(MenuReportOptions):

    """
    Defines options and provides handling interface.
    """

    def __init__(self, name, dbase):
        self.__db = dbase
        self.__pid = None
        self.__min_cm = None
        self.__max_cm = None
        self.__chromosome = None
        self.__sel1_option = None
        self.__sel2_option = None
        self.__sel3_option = None
        self.__sel4_option = None
        self.__titletext = None

        MenuReportOptions.__init__(self, name, dbase)


    def get_subject(self):
        return _('Single Match Report')

#
# Build the user option menus. Each Category Name is a different tab of the report window. 
# The various types of selectors used here are: Enumerated List, Filter, Person, and String.
#
    def add_menu_options(self, menu):
        """ Add the options for the review report """
        category_name = _("Report Options")

        self.__pid = PersonOption(_("Active Person"))
        self.__pid.set_help("The center person for the DNA match.")
        menu.add_option(category_name, "pid", self.__pid)

        self.__sel3_option = NumberOption(_("Min Shared cM"),20,0,3000)
        self.__sel3_option.set_help("The minimum total shared cM to include in report.")
        menu.add_option(category_name, "min_cm", self.__sel3_option)
        
        self.__sel4_option = NumberOption(_("Max Shared cM"),1000,0,3000)
        self.__sel4_option.set_help("The maximum total shared cM to include in report.")
        menu.add_option(category_name, "max_cm", self.__sel4_option)
        
        self.__sel1_option = EnumeratedListOption(_('Chromosome'), CHROMO_ENTRY[0])
        for i in range(len(CHROMO_ENTRY)):
            self.__sel1_option.add_item(CHROMO_ENTRY[i],CHROMO_ENTRY[i])
        self.__sel1_option.set_help(_("Chromosome"))
        menu.add_option(category_name, "chromosome", self.__sel1_option)
        
        self.__sel2_option = EnumeratedListOption(_('Report Format'), STYLE_ENTRY[0])
        for i in range(len(STYLE_ENTRY)):
            self.__sel2_option.add_item(STYLE_ENTRY[i],STYLE_ENTRY[i])
        self.__sel2_option.set_help  (_("Style of report"))
        menu.add_option(category_name, "style",self.__sel2_option)

        category_name = _("Table Options")
        self.__titletext = StringOption(_("Chromosome Report"),_("Chromosome Report"))
        self.__titletext.set_help(_("Title of report"))
        menu.add_option(category_name, "titletext",self.__titletext)

#
# The style sheet for the attributes
#
    def make_default_style(self, default_style):

        # Define the title paragraph, named 'Attribute-Title', which uses a
        # 12 point, bold Sans Serif font with a paragraph that is centered

        my_font_size = 8
        """Make the default output style for the Attribute Report."""
        # Paragraph Styles
        f = FontStyle()
        f.set_size(12)
        f.set_type_face(FONT_SANS_SERIF)
        f.set_bold(1)
        p = ParagraphStyle()
        p.set_header_level(1)
        p.set_bottom_border(1)
        p.set_top_margin(utils.pt2cm(3))
        p.set_bottom_margin(utils.pt2cm(3))
        p.set_font(f)
        p.set_alignment(PARA_ALIGN_CENTER)
        p.set_description(_("The style used for the title."))
        default_style.add_paragraph_style("Single-Attribute-Title", p)

        f = FontStyle()
        f.set_size(10)
        f.set_type_face(FONT_SANS_SERIF)
        f.set_bold(1)
        p = ParagraphStyle()
        p.set_font(f)
        p.set_alignment(PARA_ALIGN_CENTER)
        p.set_description(_("The style used for the chromosome subtitle."))
        default_style.add_paragraph_style("Single-Attribute-SubTitle", p)

        font = FontStyle()
        font.set_size(my_font_size)
        p = ParagraphStyle()
        p.set(first_indent=0, lmargin=0)
        p.set_font(font)
        p.set_top_margin(utils.pt2cm(1))
        p.set_bottom_margin(utils.pt2cm(1))
        p.set_description(_('The basic style used for the text display.'))
        default_style.add_paragraph_style("Single-Attribute-Normal", p)

        font = FontStyle()
        font.set_size(my_font_size)
        p = ParagraphStyle()
        p.set(first_indent=0, lmargin=0)
        p.set_font(font)
        p.set_alignment(PARA_ALIGN_RIGHT)
        p.set_top_margin(utils.pt2cm(1))
        p.set_bottom_margin(utils.pt2cm(1))
        p.set_description(_('The basic style used for the text display.'))
        default_style.add_paragraph_style("Single-Attribute-Normal-Right", p)

        font = FontStyle()
        font.set_size(my_font_size)
        font.set_bold(True)
        p = ParagraphStyle()
        p.set(first_indent=0, lmargin=0)
        p.set_font(font)
        p.set_top_margin(utils.pt2cm(3))
        p.set_bottom_margin(utils.pt2cm(3))
        p.set_description(_('The basic style used for table headings.'))
        default_style.add_paragraph_style("Single-Attribute-Normal-Bold", p)

        font = FontStyle()
        font.set_size(my_font_size)
        font.set_bold(True)
        p = ParagraphStyle()
        p.set(first_indent=0, lmargin=0)
        p.set_font(font)
        p.set_alignment(PARA_ALIGN_RIGHT)
        p.set_top_margin(utils.pt2cm(3))
        p.set_bottom_margin(utils.pt2cm(3))
        p.set_description(_('The basic style used for table headings.'))
        default_style.add_paragraph_style("Single-Attribute-Normal-Bold-Right", p)
        #Table Styles
        cell = TableCellStyle()
        default_style.add_cell_style('Single-Attribute-TableCell', cell)

        table = TableStyle()
        table.set_width(100)
        table.set_columns(6)
        table.set_column_width(0,10)
        table.set_column_width(1,10)
        table.set_column_width(2,15)
        table.set_column_width(3,35)
        table.set_column_width(4,15)
        table.set_column_width(5,15)
        default_style.add_table_style('Single-Attribute-Table',table)
