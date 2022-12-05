# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2020      Gary Griffin <genealogy@garygriffin.net>
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

"""Sample Report"""
#
# This is a sample report that can be used as a template. It includes many functions that a report may desire - filtered lists, options, and footers. 
# This is more documented than most code to assist in learning
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
from gramps.gen.plug.menu import (EnumeratedListOption, StringOption, NumberOption, FilterOption, PersonOption, BooleanOption)
from gramps.gen.plug.report import stdoptions
from gramps.gen.proxy import CacheProxyDb
from gramps.gen.display.name import displayer as _nd
from gramps.gen.datehandler import get_date
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback
from gramps.gen.utils.alive import probably_alive, probably_alive_range

from gramps.gen.const import (PROGRAM_NAME, VERSION)
import time
#------------------------------------------------------------------------
#
# Constants
#
#------------------------------------------------------------------------
EMPTY_ENTRY = "_____________"
#
# List of available reports 
#
PROPERTY_ENTRY = {
'Attributes with Values': ['Object','ID', 'Attribute','Value','Desc'],
'Associations': ['Type','Person ID','Person','Associate ID','Associate'],
'Birth with Date and Location': ['Location','Date','Person ID','Person', 'Primary + Secondary Citations'],
'Death with Date and Location': ['Location','Date','Person ID','Person', 'Primary + Secondary Citations']
}
#
# List of output formats
#
STYLE_ENTRY = 'Table format','CSV format'

#------------------------------------------------------------------------
#
# SampleReport. This class much match the reference in the .gpr.py file
#
#------------------------------------------------------------------------


class SampleReport(Report):
    def __init__(self, database, options_class, user):

        Report.__init__(self, database, options_class, user)
        self._user = user
        menu = options_class.menu
        mgobn = lambda name:options_class.menu.get_option_by_name(name).get_value()
#
# Initialize the user controls
#
        self.property = mgobn('property')
        self.style = mgobn('style')
        self.titletext = mgobn('titletext')
        self.filter_option = menu.get_option_by_name('filter')
        self.filter = self.filter_option.get_filter()
        pid = mgobn('pid')
        self.center_person = self.database.get_person_from_gramps_id(pid)
        if self.center_person is None:
            raise ReportError(_("Person %s is not in the Database") % pid)
        self.database = CacheProxyDb(self.database)
#
# Initialize the footer
#
        self.__init_meta(options_class)
#
# Overarrching Report writer. It selects which spscific report is requested.
#
    def write_report(self):
        property_keys = list(PROPERTY_ENTRY)
#
# Select which report based on user selection
#
        if self.property == property_keys[0]:
            reportRows = self.__process_attributes()
        elif self.property == property_keys[1]:
            reportRows = self.__process_associations()
        elif self.property == property_keys[2]:
            reportRows = self.__process_birth_death()
        elif self.property == property_keys[3]:
            reportRows = self.__process_birth_death()
#
# Select output format based on user selection
#
        if self.style == STYLE_ENTRY[0]:
            self.__write_report_table(reportRows)
        if self.style == STYLE_ENTRY[1]:
            self.__write_report_csv(reportRows)
#
# The report prefix for this report is Sample. This must be unique among all reports if it is included in a book. 
#
    def __write_report_table(self,reportRowsSorted):
        self.doc.start_paragraph("Sample-Attribute-Title")
        title = _("Review")
        mark = IndexMark(title, INDEX_TYPE_TOC,1)
        self.doc.write_text(_(self.titletext),mark)
        self.doc.end_paragraph()
        self.doc.start_table('Attributes','Sample-Attribute-Table')
        headers = PROPERTY_ENTRY.get(self.property)
        self.doc.start_row()
        for i in range(len(headers)):
            self.doc.start_cell('Sample-Attribute-TableCell')
            self.doc.start_paragraph('Sample-Attribute-Normal-Bold')
            self.doc.write_text(_(headers[i]))
            self.doc.end_paragraph()
            self.doc.end_cell()
        self.doc.end_row()
        for reportRow in reportRowsSorted :
            self.doc.start_row()
            for i in range(len(reportRow)):
                self.doc.start_cell('Sample-Attribute-TableCell')
                self.doc.start_paragraph('Sample-Attribute-Normal')
                self.doc.write_text(reportRow[i])
                self.doc.end_paragraph()
                self.doc.end_cell()
            self.doc.end_row()
        self.doc.end_table()
        self.__write_meta()

    def __write_report_csv(self, reportRowsSorted):

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(_(PROPERTY_ENTRY.get(self.property)))
        for reportRow in reportRowsSorted :
            writer.writerow(reportRow)
        self.doc.start_paragraph('Sample-Attribute-Normal')
        self.doc.write_text(output.getvalue())
        self.doc.end_paragraph()

    def __process_attributes(self):
        reportRows = []
    #
    #    Traverse Person list
    #
        cursor = self.database.get_person_cursor()

        data = cursor.first()
        while data:
            person = Person()
            person.unserialize(data[1])
            attrs = person.get_attribute_list()
            for attr in attrs:
                if attr.get_type() != "_UID":
                    reportRows.append(["Person",person.get_gramps_id(),attr.get_type().type2base(),attr.get_value(),_nd.display(person)])
            data = cursor.next()
        cursor.close()
    #
    #    Traverse Family list
    #
        cursor = self.database.get_family_cursor()

        data = cursor.first()
        while data:
            family = Family()
            family.unserialize(data[1])
            attrs = family.get_attribute_list()
            for attr in attrs:
                mother = ""
                father = ""
                if family.get_mother_handle() is not None:
                    mother = _nd.display(self.database.get_person_from_handle(family.get_mother_handle()))
                if family.get_father_handle() is not None:
                    father = _nd.display(self.database.get_person_from_handle(family.get_father_handle()))
                if attr.get_type() != "_UID":
                    reportRows.append(["Family",family.get_gramps_id(),attr.get_type().type2base(),attr.get_value(),father + " / " + mother])
            data = cursor.next()
        cursor.close()
    #
    #    Traverse Event list
    #
        cursor = self.database.get_event_cursor()

        data = cursor.first()
        while data:
            event = Event()
            event.unserialize(data[1])
            attrs = event.get_attribute_list()
            etype = event.get_type()
            for attr in attrs:
                reportRows.append(["Event - " + etype.string,event.get_gramps_id(),attr.get_type().type2base(),attr.get_value(),event.get_description()])
            data = cursor.next()
        cursor.close()
    #
    #    Traverse Media list
    #
        cursor = self.database.get_media_cursor()
    
        data = cursor.first()
        while data:
            media = Media()
            media.unserialize(data[1])
            attrs = media.get_attribute_list()
            for attr in attrs:
                reportRows.append(["Media",media.get_gramps_id(),attr.get_type().type2base(),attr.get_value(),media.get_description()])
            data = cursor.next()
        cursor.close()

        reportRowsSorted = sorted (reportRows, reverse = False)
        return reportRowsSorted

    def __process_associations(self) :
        reportRows = []
    #
    #    Traverse Person list
    #
        people = self.database.iter_person_handles()
        people = self.filter.apply(self.database, people, user=self._user)
        with self._user.progress(_('Associations Report'),_('Processing Filtered Persons...'), len(people)) as step:
            for person_handle in people:
                step()
                person = self.database.get_person_from_handle(person_handle)
                for assoc in person.get_person_ref_list():
                    associate = self.database.get_person_from_handle(assoc.ref)
                    reportRows.append([assoc.get_relation(), person.get_gramps_id(), _nd.display(person), associate.get_gramps_id(), _nd.display(associate)])
        reportRowsSorted = sorted (reportRows, reverse = False)
        return reportRowsSorted

    def __process_birth_death(self):
        reportRows = []
    #
    #    Traverse Person list
    #

        property_keys = list(PROPERTY_ENTRY)
        people = self.database.iter_person_handles()
        people = self.filter.apply(self.database, people, user=self._user)
        with self._user.progress(_('Birth / Death Report'),_('Processing Filtered Persons...'), len(people)) as step:
            for person_handle in people:
                step()
                person = self.database.get_person_from_handle(person_handle)
                bd_event = None
                if self.property == property_keys[2]:
                    bd_event = get_birth_or_fallback(self.database,person)
                    primary_event = [EventType.BIRTH]
                    secondary_event = [EventType.CHRISTEN,EventType.BAPTISM]
                elif self.property == property_keys[3]:
                    bd_event = get_death_or_fallback(self.database,person)
                    primary_event = [EventType.DEATH]
                    secondary_event = [EventType.BURIAL,EventType.CREMATION,EventType.CAUSE_DEATH]
                if bd_event:
                    place_handle = bd_event.get_place_handle()
                    if place_handle:
                        place = self.database.get_place_from_handle(place_handle)
                        if place:
                            place_title = place_displayer.display(self.database, place)
                            if place_title != "":
                                primary_cit = 0
                                secondary_cit = 0
                                for event_ref in person.get_primary_event_ref_list():
                                    if event_ref:
                                        event = self.database.get_event_from_handle(event_ref.ref)
                                        if (event and event_ref.role.is_primary()):
                                            if event.type in primary_event:
                                                primary_cit += len(event.get_citation_list())
                                            if event.type in secondary_event:
                                                secondary_cit += len(event.get_citation_list())
                                cits = "{0} + {1}".format( primary_cit, secondary_cit)
                                bd_date = bd_event.get_date_object().to_calendar("gregorian")
                                if (bd_date and bd_date.get_valid() and not bd_date.is_empty()):
                                    date_str = "%s" % get_date(bd_event)
                                    reportRows.append([place_title, date_str, person.get_gramps_id(), _nd.display(person), cits])

        reportRowsSorted = sorted (reportRows, reverse = False)
        return reportRowsSorted

    def __init_meta(self, options_class):
#
#    Footer Characteristics user-selection
#
        mgobn = lambda name:options_class.menu.get_option_by_name(name).get_value()

        self.footer_date = mgobn('footerdate')
        self.footer_version = mgobn('footerversion')
        self.footer_tree = mgobn('footertree')
#
# output footer if selected
#
    def __write_meta(self):
        self.doc.start_paragraph('Sample-Attribute-Normal')
        if self.footer_date:
            self.doc.write_text("Todays Date : %s \n" % time.ctime())
        if self.footer_version:
            self.doc.write_text("Gramps Version: %s \n" % VERSION)
        if self.footer_tree:
            self.doc.write_text("Gramps Tree: %s \n" % self.database.get_dbname())
        self.doc.end_paragraph()



#------------------------------------------------------------------------
#
# Sample Report Options - this class must be the same as specified in the .gpr.py file
#
#------------------------------------------------------------------------
class SampleReportOptions(MenuReportOptions):

    """
    Defines options and provides handling interface.
    """

    def __init__(self, name, dbase):
        self.__db = dbase
        self.__pid = None
        self.__filter = None
        self.__sel1_option = None
        self.__sel2_option = None
        self.__titletext = None
        self.__footer_date = None
        self.__footer_version = None
        self.__footer_tree = None
        MenuReportOptions.__init__(self, name, dbase)


    def get_subject(self):
        return _('Sample Report')

#
# Build the user option menus. Each Category Name is a different tab of the report window. 
# The various types of selectors used here are: Enumerated List, Filter, Person, and String.
#
    def add_menu_options(self, menu):
        """ Add the options for the review report """
        category_name = _("Report Options")
        property_keys = list(PROPERTY_ENTRY)
        self.__sel1_option = EnumeratedListOption(_('Property to be reviewed'), property_keys[0])
        for i in range(len(property_keys)):
            self.__sel1_option.add_item(property_keys[i],property_keys[i])
        self.__sel1_option.set_help  (_("Property to be reviewed"))

        menu.add_option(category_name, "property",self.__sel1_option)
        self.__filter = FilterOption(_("Filter"), 0)
        self.__filter.set_help(
            _("Select the person filter to be applied to the report."))
        menu.add_option(category_name,"filter", self.__filter)

        self.__filter.connect('value-changed', self.__filter_changed)
        self.__pid = PersonOption(_("Filter Person"))
        self.__pid.set_help("The center person for the filter.")
        menu.add_option(category_name, "pid", self.__pid)
        self.__pid.connect('value-changed',self.__update_filters)

        self.__sel1_option.connect('value-changed',self.__property_changed)
        self.__sel2_option = EnumeratedListOption(_('Report Format'), STYLE_ENTRY[0])
        for i in range(len(STYLE_ENTRY)):
            self.__sel2_option.add_item(STYLE_ENTRY[i],STYLE_ENTRY[i])
        self.__sel2_option.set_help  (_("Style of report"))
        menu.add_option(category_name, "style",self.__sel2_option)

        category_name = _("Table Options")
        self.__titletext = StringOption(_("Title text"),_("Title text"))
        self.__titletext.set_help(_("Title of report"))
        menu.add_option(category_name, "titletext",self.__titletext)

        self.__add_menu_meta(menu)

    def __update_filters(self):
        """
        Update the filter list based on the selected person
        """
        gid = self.__pid.get_value()
        person = self.__db.get_person_from_gramps_id(gid)
        filter_list = utils.get_person_filters(person,
                                               include_single=False)
        self.__filter.set_filters(filter_list)

    def __filter_changed(self):
        """
        Handle filter change. If the filter is not specific to a person,
        disable the person option
        """
        filter_value = self.__filter.get_value()
        if filter_value == 0: # "Entire Database" (as "include_single=False")
            self.__pid.set_available(False)
        else:
            # The other filters need a center person (assume custom ones too)
            self.__pid.set_available(True)

    def __property_changed(self):
        """
        Handle property change. 
            If the property is not Census Report, disable the Census options visibility
            If the property is an Attribute Report, disable the Person filter visibility
        """
        property_value = self.__sel1_option.get_value()
        if property_value == list(PROPERTY_ENTRY)[0]: # "Attribute Report is the only report that does not use a Person filter" 
            self.__filter.set_available(False)
            self.__pid.set_available(False)
        else:
            self.__filter.set_available(True)
            self.__filter_changed()

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
        default_style.add_paragraph_style("Sample-Attribute-Title", p)

        font = FontStyle()
        font.set_size(my_font_size)
        p = ParagraphStyle()
        p.set(first_indent=0, lmargin=0)
        p.set_font(font)
        p.set_top_margin(utils.pt2cm(1))
        p.set_bottom_margin(utils.pt2cm(1))
        p.set_description(_('The basic style used for the text display.'))
        default_style.add_paragraph_style("Sample-Attribute-Normal", p)

        font = FontStyle()
        font.set_size(my_font_size)
        p = ParagraphStyle()
        p.set(first_indent=0, lmargin=0)
        p.set_font(font)
        p.set_alignment(PARA_ALIGN_RIGHT)
        p.set_top_margin(utils.pt2cm(1))
        p.set_bottom_margin(utils.pt2cm(1))
        p.set_description(_('The basic style used for the text display.'))
        default_style.add_paragraph_style("Sample-Attribute-Normal-Right", p)

        font = FontStyle()
        font.set_size(my_font_size)
        font.set_bold(True)
        p = ParagraphStyle()
        p.set(first_indent=0, lmargin=0)
        p.set_font(font)
        p.set_top_margin(utils.pt2cm(3))
        p.set_bottom_margin(utils.pt2cm(3))
        p.set_description(_('The basic style used for table headings.'))
        default_style.add_paragraph_style("Sample-Attribute-Normal-Bold", p)

        #Table Styles
        cell = TableCellStyle()
        default_style.add_cell_style('Sample-Attribute-TableCell', cell)

        table = TableStyle()
        table.set_width(100)
        table.set_columns(5)
        table.set_column_width(0,12)
        table.set_column_width(1,8)
        table.set_column_width(2,20)
        table.set_column_width(3,25)
        table.set_column_width(4,35)
        default_style.add_table_style('Sample-Attribute-Table',table)

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
        self.__update_filters()
