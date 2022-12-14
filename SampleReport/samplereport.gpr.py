register(REPORT,
    id   = 'sample report',
    name = _('Sample Report'),
    description = _("Produces a catalog of specified objects."),
    version = '0.6.0',
    gramps_target_version = '5.1',
    status = STABLE,
    fname = 'samplereport.py',
    authors = ["Gary Griffin"],
    authors_email = ["genealogy@garygriffin.net"],
    category = CATEGORY_TEXT,
    reportclass = 'SampleReport',
    optionclass = 'SampleReportOptions',
    report_modes = [REPORT_MODE_GUI, REPORT_MODE_BKI, REPORT_MODE_CLI],
    require_active = False
    )
