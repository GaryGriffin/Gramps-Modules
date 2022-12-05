# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2020-2022      Gary Griffin <genealogy@garygriffin.net>
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

"""DNA Relationship Report"""
#
#
# Note: from Roberta Estes blog: https://dna-explained.com/2020/04/09/shared-cm-project-2020-analysis-comparison-handy-reference-charts/
#
# Different companies report DNA in different ways in addition to having different matching thresholds. 
# For example, Family Tree DNA includes in your match total all DNA to 1 cM that you share with a match 
# over the matching threshold. Conversely, Ancestry has a lower matching threshold, but often strips 
# out some matching DNA using Timber. 23andMe counts fully identical segments twice and reports the 
# X chromosome in their totals. MyHeritage does not report the X chromosome. 
# There is no “right” or “wrong,” or standardization, simply different approaches. 
# Hopefully, the variances will be removed or smoothed in the averages.
#
#------------------------------------------------------------------------
#
# standard python modules
#
#------------------------------------------------------------------------
import math

#------------------------------------------------------------------------
#
# Gramps modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.errors import ReportError
from gramps.gen.lib import (Person)
from gramps.gen.plug.docgen import (IndexMark, FontStyle, ParagraphStyle,
                                    TableStyle, TableCellStyle,
                                    FONT_SANS_SERIF, FONT_SERIF,
                                    INDEX_TYPE_TOC, PARA_ALIGN_CENTER, PARA_ALIGN_RIGHT)
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import utils
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.menu import BooleanOption
from gramps.gen.plug.report import stdoptions
from gramps.gen.proxy import CacheProxyDb
from gramps.gen.display.name import displayer as _nd
from gramps.gen.relationship import get_relationship_calculator
import re
from gramps.gen.const import (PROGRAM_NAME, VERSION)
import time
#------------------------------------------------------------------------
#
# Constants
#
#------------------------------------------------------------------------
EMPTY_ENTRY = "_____________"

#------------------------------------------------------------------------
#
# DetAncestorReport
#
#------------------------------------------------------------------------


class RelationshipDNA(Report):
    def __init__(self, database, options_class, user):

        Report.__init__(self, database, options_class, user)
        self.map = {}
        self._user = user
        self.__footer_date = None
        self.database = CacheProxyDb(self.database)
        self.db = self.database
        uistate = user.uistate
        self.person = self.db.get_person_from_handle(
                                            uistate.get_active('Person'))
        menu = options_class.menu
        mgobn = lambda name:options_class.menu.get_option_by_name(name).get_value()
#
#    Census report has an additional user-selection tab
#
        self.printID = mgobn('grampsID')
        self.printSEG = mgobn('segments')
        self.printKIT = mgobn('kit')
        self.__init_meta(options_class)

    def write_report(self):

        cursor = self.database.get_person_cursor()

        data = cursor.first()

        self.relationship = get_relationship_calculator(glocale)
        self.doc.start_paragraph("DNA-Title")
        self.doc.write_text(_("DNA overlap with relationships for {} sorted by cM".format(_nd.display(self.person))))
        self.doc.end_paragraph()
        
        self.doc.start_table('DNATable','DNA-Table')
        self.doc.start_row()

        self.doc.start_cell('DNA-TableCell')
        self.doc.start_paragraph('DNA-Normal-Bold')
        self.doc.write_text(_("cM"))
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.start_cell('DNA-TableCell')
        self.doc.start_paragraph('DNA-Normal-Bold')
        self.doc.write_text(_("Name"))
        self.doc.end_paragraph()
        self.doc.end_cell()
        if self.printKIT:
            self.doc.start_cell('DNA-TableCell')
            self.doc.start_paragraph('DNA-Normal-Bold')
            self.doc.write_text(_("Ancestry ID / DNA kit"))
            self.doc.end_paragraph()
            self.doc.end_cell()

        self.doc.start_cell('DNA-TableCell')
        self.doc.start_paragraph('DNA-Normal-Bold')
        self.doc.write_text(_("Relationship"))
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.start_cell('DNA-TableCell')
        self.doc.start_paragraph('DNA-Normal-Bold')
        self.doc.write_text(_("Common Ancestor"))
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.end_row()

        reportRows = []
        active = self.person
        for assoc in active.get_person_ref_list():
            if assoc.get_relation() == 'DNA':
                associate = self.db.get_person_from_handle(assoc.ref)
                attrs = associate.get_attribute_list()
                AncestryID = ''
                DNAkit = ''
                for attr in attrs:
                    attr_name = attr.get_type().type2base()
                    if attr_name == 'Ancestry ID':
                        AncestryID = attr.get_value()
                    if attr_name == 'DNAkit':
                        DNAkit = attr.get_value()
                commontext = ''
                rel_string = ''
                rel_strings , common_an = self.relationship.get_all_relationships(self.db,self.person,associate)
                if len(rel_strings) > 0 :
                    rel_string = rel_strings[0]
                    common = common_an[0]
                    length = len(common)
                    if length == 1:
                        p1 = self.db.get_person_from_handle(common[0])
                        if common[0] in [associate.handle, self.person.handle]:
                            commontext = ''
                        else :
                            name = _nd.display(p1)
                            commontext = " " + _("%s") % name
                    elif length >= 2:
                        p1str = _nd.display(self.db.get_person_from_handle(common[0]))
                        p2str = _nd.display(self.db.get_person_from_handle(common[1]))
                        commontext = " " + _("%(ancestor1)s and %(ancestor2)s") % {
                                          'ancestor1': p1str,
                                          'ancestor2': p2str
                                          }                            
                for handle in assoc.get_note_list():
                    note = self.db.get_note_from_handle(handle)
#
# Either get a single number in a single line or get a list of segments
#
                    cM = 0
                    seg_count = 'Seg'
                    for line in note.get().split('\n'):
                        if re.search('\t',line) != None:
                            line2 = re.sub(',','',line)
                            line = re.sub('\t',',',line2)
                        field = line.split(',')
                        if len(field) == 1:   # single cM entry
                            seg_count = 'Overall'
                            try:
                                cM = float(field[0])
                            except ValueError:
                                continue
                        elif len(field) >= 4:   # shared segment info
                            try:
                                cM += float(field[3])
                            except:
                                continue
                    IDstring = AncestryID + ' / '+ DNAkit
                    NameString = _nd.display(associate) 
                    if self.printID:
                        NameString += ' [' + associate.get_gramps_id() + ']'
                    if self.printSEG:
                        NameString += ' (' + seg_count + ')'
                    reportRows.append([cM,NameString,IDstring,rel_string,commontext])
#                    try:
#                        reportRows.append([float(cM),NameString,IDstring,rel_string,commontext])
#                    except ValueError:
#                        reportRows.append([-1,NameString,IDstring,"Bad cM value in Association Note",commontext])
        reportRowsSorted = sorted (reportRows, reverse = True)

        for reportRow in reportRowsSorted :

            self.doc.start_row()

            self.doc.start_cell('DNA-TableCell')
            self.doc.start_paragraph('DNA-Normal')
            if reportRow[0] >= 100:
                self.doc.write_text(str(int(reportRow[0])))
            else:
                self.doc.write_text(str(round(reportRow[0],1)))
            self.doc.end_paragraph()
            self.doc.end_cell()

            self.doc.start_cell('DNA-TableCell')
            self.doc.start_paragraph('DNA-Normal')
            self.doc.write_text(reportRow[1])
            self.doc.end_paragraph()
            self.doc.end_cell()

            if self.printKIT:
                self.doc.start_cell('DNA-TableCell')
                self.doc.start_paragraph('DNA-Normal')
                self.doc.write_text(reportRow[2])
                self.doc.end_paragraph()
                self.doc.end_cell()

            self.doc.start_cell('DNA-TableCell')
            self.doc.start_paragraph('DNA-Normal')
            self.doc.write_text(reportRow[3])
            self.doc.end_paragraph()
            self.doc.end_cell()
                    
            self.doc.start_cell('DNA-TableCell')
            self.doc.start_paragraph('DNA-Normal')
            self.doc.write_text(reportRow[4])
            self.doc.end_paragraph()
            self.doc.end_cell()

            self.doc.end_row()

        self.doc.end_table()
        self.__write_meta()

    def __init_meta(self, options_class):
#
#    Report Characteristics user-selection
#
        mgobn = lambda name:options_class.menu.get_option_by_name(name).get_value()

        self.footer_date = mgobn('footerdate')
        self.footer_version = mgobn('footerversion')
        self.footer_tree = mgobn('footertree')
    
    def __write_meta(self):
        self.doc.start_paragraph('DNA-Normal')
        self.doc.write_text("\n\n")
        if self.footer_date:
            self.doc.write_text("Todays Date : %s \n" % time.ctime())
        if self.footer_version:
            self.doc.write_text("Gramps Version: %s \n" % VERSION)
        if self.footer_tree:
            self.doc.write_text("Gramps Tree: %s \n" % self.database.get_dbname())
        self.doc.write_text("\n\nOverall --> Single cM value specified")
        self.doc.write_text("\nSeg --> Segment values specified")
        self.doc.end_paragraph()


#------------------------------------------------------------------------
#
# RelationshipDNA Options
#
#------------------------------------------------------------------------
class RelationshipDNAOptions(MenuReportOptions):

    """
    Defines options and provides handling interface.
    """

    def __init__(self, name, dbase):
        self.__db = dbase
        self.__pid = None
        MenuReportOptions.__init__(self, name, dbase)

    def make_default_style(self, default_style):

        # Define the title paragraph, named 'DNA-Title', which uses a
        # 16 point, bold Sans Serif font with a paragraph that is centered


        """Make the default output style for the DNA Report."""
        # Paragraph Styles
        f = FontStyle()
        f.set_size(16)
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
        default_style.add_paragraph_style("DNA-Title", p)

        font = FontStyle()
        font.set_size(8)
        p = ParagraphStyle()
        p.set(first_indent=-0.75, lmargin=.25)
        p.set_font(font)
        p.set_top_margin(utils.pt2cm(1))
        p.set_bottom_margin(utils.pt2cm(1))
        p.set_description(_('The basic style used for the text display.'))
        default_style.add_paragraph_style("DNA-Normal", p)

        font = FontStyle()
        font.set_size(8)
        p = ParagraphStyle()
        p.set(first_indent=-0.75, lmargin=.25)
        p.set_font(font)
        p.set_alignment(PARA_ALIGN_RIGHT)
        p.set_top_margin(utils.pt2cm(1))
        p.set_bottom_margin(utils.pt2cm(1))
        p.set_description(_('The basic style used for the text display.'))
        default_style.add_paragraph_style("DNA-Normal-Right", p)

        font = FontStyle()
        font.set_size(8)
        font.set_bold(True)
        p = ParagraphStyle()
        p.set(first_indent=-0.75, lmargin=.25)
        p.set_font(font)
        p.set_top_margin(utils.pt2cm(3))
        p.set_bottom_margin(utils.pt2cm(3))
        p.set_description(_('The basic style used for table headings.'))
        default_style.add_paragraph_style("DNA-Normal-Bold", p)

        #Table Styles
        cell = TableCellStyle()
        default_style.add_cell_style('DNA-TableCell', cell)

        table = TableStyle()
        table.set_width(100)
        table.set_columns(5)
        table.set_column_width(0, 4)
        table.set_column_width(1, 18)
        table.set_column_width(2, 18)
        table.set_column_width(3, 22)
        table.set_column_width(4, 38)
        default_style.add_table_style('DNA-Table',table)

    def add_menu_options(self, menu):
        """ Add the options for the review report """
        category_name = _("Report Options")

        self.printID = BooleanOption(_("Print gramps ID"),True)
        self.printID.set_help(_("Include gramps ID with the name"))
        menu.add_option(category_name,"grampsID",self.printID)
        self.printSEG = BooleanOption(_("Print segment flag"),True)
        self.printSEG.set_help(_("Flag whether segment info in Association Note"))
        menu.add_option(category_name,"segments",self.printSEG)
        self.printKIT = BooleanOption(_("Print Kit Info"),True)
        self.printKIT.set_help(_("Print Ancestry ID and GEDmatch kit (if available)"))
        menu.add_option(category_name,"kit",self.printKIT)


        self.__add_menu_meta(menu)

    def __add_menu_meta(self,menu):
        category_name = _("Report Stats")
        self.__footer_date = BooleanOption(_("Show Date"),False)
        self.__footer_date.set_help(_("Show Date at end of report"))
        menu.add_option(category_name,"footerdate", self.__footer_date)
        self.__footer_version = BooleanOption (_("Show Gramps Version"), False)
        self.__footer_version.set_help(_("Show Gramps Version at end of report"))
        menu.add_option(category_name,"footerversion", self.__footer_version)
        self.__footer_tree = BooleanOption(_("Show Gramps Tree"), False)
        self.__footer_tree.set_help(_("Show Gramps Tree name at end of report"))
        menu.add_option(category_name,"footertree", self.__footer_tree)
