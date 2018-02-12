import re
from ..shared import html

re_word_with_space = re.compile('[^\s^\w]')
def _get_section_name_s(section_name):
    section_name = re_word_with_space.sub('', section_name)
    return section_name.replace(' ', '_').lower()

def _get_hide_tbl_script(name, section_s_list, init_id):
    ''' @override html.get_hide_tbl_scrip
        @note make sure section name in section_s_list is the same as the one used in 
        get_tbl_header
    
    '''
    if init_id < 0:
        init_id = 0
    fcn_name = 'show_%s' % (name)
    var_name = 'last_%s_id' % (name)
    body = ''
    for section_name in section_s_list:
        id_name = ''.join([name, '_', section_name])
        body = body + '''       $(document.getElementById("%s"+%s)).hide();
        $(document.getElementById("%s"+id)).fadeIn();\n''' % (id_name, var_name, id_name)
    return fcn_name,'''<script>
    var %s=%d;
    function %s(id) {
        if (%s === id) {
            return;
        }
        %s
        %s=id;
    } 
  </script>''' % (var_name, init_id, fcn_name, var_name, body, var_name)

def _get_phy_nav_tab(hide_tbl_fcn_name, ossp_phy_list):
    color = 'green'
    nav_tab_script = '  <ul class="nav nav-tabs">'
    for ossp_id, this_phy_list in ossp_phy_list:
        this_ossp = ''
        for phy_id in this_phy_list:
            clickable = ' onclick="%s(%d)"' % (hide_tbl_fcn_name, phy_id)
            this_nav_tab = '<li><a%s style="color:%s;"><b>PHY %d</b></a></li>' % \
                            (clickable, color, phy_id)
            this_ossp = ''.join([this_ossp, this_nav_tab])
        this_ossp = ('<li class="dropdown"><a class="dropdown-toggle" data-toggle="dropdown" href="#">OSSP {} '
        '<span class="caret"></span></a><ul class="dropdown-menu">{}</ul></li>').format(ossp_id, this_ossp)
        nav_tab_script = ''.join([nav_tab_script, this_ossp])
    return nav_tab_script

def _get_ossp_nav_tab(hide_tbl_fcn_name, ossp_list):
    color = 'green'
    nav_tab_script = '  <ul class="nav nav-tabs">'
    this_ossp = ''
    for ossp_id in ossp_list:
        clickable = ' onclick="%s(%d)"' % (hide_tbl_fcn_name, ossp_id)
        this_nav_tab = '<li><a%s style="color:%s;"><b>OSSP %d</b></a></li>' % \
                        (clickable, color, ossp_id)
        this_ossp = ''.join([this_ossp, this_nav_tab])
    this_ossp = ('<li class="dropdown"><a class="dropdown-toggle" data-toggle="dropdown" href="#">OSSP'
    '<span class="caret"></span></a><ul class="dropdown-menu">{}</ul></li>').format(this_ossp)
    nav_tab_script = ''.join([nav_tab_script, this_ossp])
    return nav_tab_script

PER_PHY_TBL_PREFIX = 'ossp_per_phy'
PER_OSSP_TBL_PREFIX = 'per_ossp'
global_phy_nav_tab = ''
def get_top_level_header(input_filename, section_list, per_phy_section_list, ossp_phy_list):
    common_scripts = html.get_common_scripts()
    hide_sec_scripts = ''
    click_link = ''
    ossp_hide_tbl_script = ''
    phy_hide_tbl_script = ''
    ossp_nav_tab = ''
    hqa_nav_tab = ''
    global global_phy_nav_tab
    if not section_list and not per_phy_section_list:
        raise AssertionError('No section list specified')

    # register section not per PHY
    if section_list:
        section_s_list = list(map(lambda x: _get_section_name_s(x), section_list))
        hide_sec_scripts = html.get_hide_section_scripts(section_s_list)
        for section, section_s in zip(section_list, section_s_list):
            template = '<p style="color:green;">Click to get <a href="#{}">{}</a></p>'\
            .format(section_s, section.strip(':').replace('_', ' ').upper())
            click_link = ''.join([click_link,template])
        if ossp_phy_list:
            hide_tbl_fcn_name, ossp_hide_tbl_script = _get_hide_tbl_script(PER_OSSP_TBL_PREFIX, section_s_list, 0)
            ossp_nav_tab = _get_ossp_nav_tab(hide_tbl_fcn_name, list(map(lambda x: x[0], ossp_phy_list)))
            del hide_tbl_fcn_name
    # register section per PHY
    if per_phy_section_list:
            per_phy_section_s_list = list(map(lambda x: _get_section_name_s(x), per_phy_section_list))
            hide_sec_scripts = ''.join([hide_sec_scripts, html.get_hide_section_scripts(per_phy_section_s_list)])
            for section, section_s in zip(per_phy_section_list, per_phy_section_s_list):
                template = '<p style="color:green;">Click to get <a href="#{}">{}</a></p>'\
                .format(section_s, section.strip(':').replace('_', ' ').upper())
                click_link = ''.join([click_link,template])
            if ossp_phy_list:
                hide_tbl_fcn_name, phy_hide_tbl_script = _get_hide_tbl_script(PER_PHY_TBL_PREFIX, per_phy_section_s_list, 0)
                phy_nav_tab = _get_phy_nav_tab(hide_tbl_fcn_name, ossp_phy_list)
                global_phy_nav_tab = '<div class="container">{}</div>'.format(phy_nav_tab)
                del hide_tbl_fcn_name
    return \
'''<!DOCTYPE html>
<html lang="en">
<head>
  <title>Decoded OSSP Register Dump</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  %s
  %s
  %s
  %s
</head>
<style>
    table, th, td {
        border: 1px solid black;
    }
    pre {
        white-space: pre-wrap;       /* Since CSS 2.1 */
        white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */
        white-space: -pre-wrap;      /* Opera 4-6 */
        white-space: -o-pre-wrap;    /* Opera 7 */
        word-wrap: break-word;       /* Internet Explorer 5.5+ */
    }
	h2   {color: black;}
	h3   {color: orange;}
    pre span {color: black;}
	p span {color: grey;}
    footer {
        position: relative;
        height: 50px;
        width: 100%%;
    }
    p.copyright {
        position: absolute;
        width: 100%%;
        color: black;
        line-height: 20px;
        font-size: 10pt;
        font-family: sans-serif;
        text-align: center;
        bottom:0;
    }
</style>
<body>
<div class="container">
<a id="top_section"><p style="color:red;">Decoded OSSP register dump:</p></a> 
<p style="color:red;">%s</p>
%s
<p style="color:red;">Internet Explore may not correctly display the result, consider using a modern browser, such as Microsoft Edge or Google Chrome.</p>
%s
</div>''' % (common_scripts, hide_sec_scripts, ossp_hide_tbl_script, phy_hide_tbl_script, input_filename, click_link, ossp_nav_tab)

def get_top_level_ending():
    return html.get_top_level_ending()

'''def get_per_phy_section_header(section_name, ossp_phy_list, first_phy_id):
    section_name_s = _get_section_name_s(section_name)
    hide_tbl_fcn_name, hqa_hide_tbl_script = html.get_hide_tbl_script(section_name_s, first_phy_id)
    hqa_nav_tab = get_ossp_nav_tab(hide_tbl_fcn_name, ossp_phy_list)
    return \
    ('{}<div class="container" id="{}"><h3 id="{}_title">{}</h3></div><div class="container" id="{}_main">'
    '<div class="container"><a href="#top_section">Back To Top</a>{}</div>')\
    .format(hqa_hide_tbl_script, section_name_s, section_name_s, section_name, section_name_s, hqa_nav_tab)'''


def get_section_header(section_name):
    section_name_s = _get_section_name_s(section_name)
    return \
    ('<div class="container" id="{}"><h3 id="{}_title">{}</h3></div>'
    '<div class="container" id="{}_main">'
    #'<div class="container"><a href="#top_section">Back To Top</a></div>'
    '<h3 style="color:red" id="{}_unique_reg_section">Unique Registers (<a href="#{}_common_reg_section">Go To Common Reg Section</a>)</h3>'\
    .format(section_name_s, section_name_s, section_name, section_name_s, section_name_s, section_name_s))

def get_section_ending(section_name):
    section_name_s = _get_section_name_s(section_name)
    return \
''' <div class="container">
  <p id="end_{}"><span>End of <a href="#{}">{}</a> section.</span></p>
  <a href="#top_section">Back To Top</a>
  </div>
  </div>'''.format(section_name_s, section_name_s, section_name)

def get_common_reg_header(section_name):
    section_name_s = _get_section_name_s(section_name)
    return '<h3 style="color:red" id="{}_common_reg_section">Common register between all OSSPs/PHYs for {} '\
           '(<a href="#{}_unique_reg_section">Go To Unique Reg Section</a>)</h3>'\
           .format(section_name_s, section_name, section_name_s)

def get_tbl_ending():
    return '  </div>\n'

def get_per_phy_tbl_header(section_name, ossp_id, phy_id, first_phy_id):
    display = 'block' if (phy_id == first_phy_id) else 'none'
    id_name = ''.join([PER_PHY_TBL_PREFIX, '_', _get_section_name_s(section_name)])
    return \
'''  <div class="container" id="%s%d" style="display:%s"><h2 align="center" style="color:orange">PHY %d (OSSP %d)</h2>'''\
    % (id_name, phy_id, display, phy_id, ossp_id)

def get_per_ossp_tbl_header(section_name, ossp_id, first_ossp_id):
    display = 'block' if (ossp_id == first_ossp_id) else 'none'
    id_name = ''.join([PER_OSSP_TBL_PREFIX, '_', _get_section_name_s(section_name)])
    return \
'''  <div class="container" id="%s%d" style="display:%s"><h2 align="center" style="color:orange">OSSP %d</h2>'''\
    % (id_name, ossp_id, display, ossp_id)
