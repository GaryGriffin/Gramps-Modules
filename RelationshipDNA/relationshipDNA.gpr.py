register(REPORT,
    id   = 'relationship DNA',
    name = _('DNA Relationship Report'),
    description = _("Produces a relationship report for all Persons with cM overlap with the active person. For each person who has a DNA overlap (as quantified in cM), create cM association for the main person and specify the associated person. Add a Note to the Association with the numeric value of the cM match between the two people. Report will display the associated person Ancestry ID attribute if present (person attribute of Ancestry ID)."),
    version = '1.0.0',
    gramps_target_version = '5.1',
    status = STABLE,
    fname = 'relationshipDNA.py',
    authors = ["Gary Griffin"],
    authors_email = ["genealogy@garygriffin.net"],
    category = CATEGORY_TEXT,
    reportclass = 'RelationshipDNA',
    optionclass = 'RelationshipDNAOptions',
    report_modes = [REPORT_MODE_GUI, REPORT_MODE_BKI, REPORT_MODE_CLI],
    require_active = True
    )

__author__ = "gary griffin"
