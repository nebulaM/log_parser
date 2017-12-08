import os
import src.msgu.msgu_common as cm

HTML_LIB_DIR = os.path.join(cm.MSGULog.INCLUDE_DIR, 'lib', 'html')

def get_stylesheet():
    filename = os.path.join(HTML_LIB_DIR, 'bootstrap.min.css')
    css = open(filename).read()
    return ''.join(['<style>', css, '</style>'])

def get_script():
    filename = os.path.join(HTML_LIB_DIR, 'jquery.min.js')
    jquery = open(filename).read()
    filename = os.path.join(HTML_LIB_DIR, 'bootstrap.min.js')
    bootstr = open(filename).read()
    return ''.join(['<script>', jquery, '</script>', \
                    '<script>', bootstr, '</script>'])

def get_common_scripts():
    return ''.join([get_stylesheet(), get_script()])

def get_hwa_standalone_header(input_filename):
    css = get_stylesheet()
    return '''<!DOCTYPE html>
    <html lang="en">
    <head>
    <title>MSGU HWA Reg Decode</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
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
        pre span {color: black;}
    </style>
    <body>

    <div class="container">
    <a id="top_section"><p style="color:red;">Decoded MSGU log from crash dump:</p></a> 
    <p style="color:red;">%s</p>
    <h3>MSGU HWA REG</h3>
    <p>The following table contains decoded register dump from crash dump for MSGU HWA register section:</p>\n''' \
    % (css, input_filename)

def get_hwa_standalone_ending():
    return \
'''</div>
</body>
</html>\n'''

def get_hqa_hide_tbl_script(first_enabled_queue):
    if first_enabled_queue < 0:
        first_queue = 0
    else:
        first_queue = first_enabled_queue
    return '''<script>
    var lastId=%d;
    function showHqa(id) {
        if (lastId === id) {
            return;
        }
        $(document.getElementById("Hqa_q"+lastId)).hide();
        $(document.getElementById("Hqa_q"+id)).fadeIn();
        lastId=id;
    } 
  </script>''' % (first_queue)

def get_hqa_nav_tab(queue_list):
    ib_admin = ''
    ib_oper = ''
    ob_admin = ''
    ob_oper = ''
    for q in queue_list:
        oper_mode = ''
        error = ''
        color = 'green'
        clickable = ' onclick="showHqa(%d)"' % (q.qid)
        highlight_0 = '<b>'
        highlight_1 = '</b>'
        if q.is_bad_q is True:
            color = 'red'
            error = ' (Error)'
        elif q.is_enabled is False:
            color = 'grey'
            clickable = ''
            highlight_0 = ''
            highlight_1 = ''
        if q.q_mode == cm.HQA_WORD.W_IB and q.q_type == cm.HQA_WORD.W_OPER:
            if q.is_enabled is True:
                oper_mode = q.status_ib_oper_q_raid_hba
            this_nav_tab = '<li><a%s style="color:%s;">%sQ %d %s%s%s</a></li>' % \
                            (clickable, color, highlight_0, q.qid, oper_mode, error, highlight_1)
            ib_oper = ''.join([ib_oper, this_nav_tab])
        elif q.q_mode == cm.HQA_WORD.W_OB and q.q_type == cm.HQA_WORD.W_OPER:
            if q.is_enabled is True:
                oper_mode = q.status_dict['int'] +'=0x{:02x}'.format(q.status_ob_oper_q_int_num)
            this_nav_tab = '<li><a%s style="color:%s;">%sQ %d %s%s%s</a></li>' % \
                            (clickable, color, highlight_0, q.qid, oper_mode, error, highlight_1)
            ob_oper = ''.join([ob_oper, this_nav_tab])
        elif q.q_type == cm.HQA_WORD.W_ADMIN:
            this_nav_tab = '<li><a%s style="color:%s;">%sQ %d%s%s</a></li>' % \
                            (clickable, color, highlight_0, q.qid, error, highlight_1)
            if q.q_mode == cm.HQA_WORD.W_IB:
                ib_admin = ''.join([ib_admin, this_nav_tab])
            else:
                ob_admin = ''.join([ob_admin, this_nav_tab])
    
    return '''  <ul class="nav nav-tabs">
  <li class="dropdown">
      <a class="dropdown-toggle" data-toggle="dropdown" href="#">IB Admin Q  <span class="caret"></span></a>
      <ul class="dropdown-menu">
        %s
      </ul>
    </li>
    <li class="dropdown">
      <a class="dropdown-toggle" data-toggle="dropdown" href="#">IB Operational Q  <span class="caret"></span></a>
      <ul class="dropdown-menu">
        %s
      </ul>
    </li>
   <li class="dropdown">
      <a class="dropdown-toggle" data-toggle="dropdown" href="#">OB Admin Q  <span class="caret"></span></a>
      <ul class="dropdown-menu">
        %s
      </ul>
    </li>
    <li class="dropdown">
      <a class="dropdown-toggle" data-toggle="dropdown" href="#">OB Operational Q  <span class="caret"></span></a>
      <ul class="dropdown-menu">
        %s
      </ul>
    </li>
  </ul>''' % (ib_admin, ib_oper, ob_admin, ob_oper)

def get_hqa_standalone_header(input_filename, queue_list, first_enabled_q):
    common_scripts = get_common_scripts()
    hqa_script = get_hqa_hide_tbl_script(first_enabled_q)
    hqa_nav_tab = get_hqa_nav_tab(queue_list)
    return \
('''<!DOCTYPE html>
<html lang="en">
<head>
  <title>MSGU HQA Reg Decode</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
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
    pre span {color: black;}
</style>
<body>
  <div class="container">
  <p style="color:red;">Decoded MSGU log from crash dump:</p> 
  <p style="color:red;">%s</p>
  <h3 id="msgu_hqa_reg">MSGU HQA REG</h3>
  <p style="color:red;">Click on a tab to select a Q, <span style="color:green;"><b>Green Qs</b></span> are enabled, <span style="color:grey;"><b>GREY Qs</b></span> are disabled.</p>
  %s
  </div>\n''' % (common_scripts, hqa_script, input_filename, hqa_nav_tab))

def get_hqa_standalone_ending():
    return \
'''<div class="container">
  <p id="end_msgu_hqa_reg">End of <a href="#msgu_hqa_reg">MSGU HQA Reg</a> section.</p>
</div>
</body>
</html>'''

def get_hqa_tbl_header(q, first_enabled_q):
    if q.qid == first_enabled_q:
        display = 'block'
    else:
        display = 'none'
    title = ''.join([q.q_mode, ' ', q.q_type, ' Queue'])
    return \
('''  <div class="container" id="Hqa_q%d" style="display:%s">
   <h2 align="center" style="color:orange">Queue %d (%s)</h2>\n''' % (q.qid, display, q.qid, title))
def get_hqa_tbl_ending():
    return '  </div>\n'

def get_lba_lbb_standalone_header(input_filename):
    css = get_stylesheet()
    return '''<!DOCTYPE html>
    <html lang="en">
    <head>
    <title>MSGU LBA LBB MEM Decode</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
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
        pre span {color: black;}
        .wrap {
            display: flex;
            justify-content: center;
            align-items: center;
        }
    </style>
    <body>

    <div class="container">
    <a id="top_section"><p style="color:red;">Decoded MSGU log from crash dump:</p></a> 
    <p style="color:red;">%s</p>
    <h3>MSGU LBA and LBB MEM</h3>
    <p>The following IU(s) are decoded from LBA and LBB memory:</p>\n''' \
    % (css, input_filename)

def get_lba_lbb_standalone_ending():
    return \
'''</div>
</body>
</html>\n'''

def get_hide_section_script(section):
    return \
'''    <script>
    var is_%(section)s_hide=false;
    $(document).ready(function(){
        $(document.getElementById("%(section)s_title")).click(function(){
    	    if (is_%(section)s_hide===false){
        	    $(document.getElementById("%(section)s_main")).hide(200);
            } else {
        	    $(document.getElementById("%(section)s_main")).show(200);
            }
            is_%(section)s_hide=!is_%(section)s_hide;
        });
    });
    </script>''' % {'section': section}

def get_hide_section_scripts(section_list):
    scripts = ''
    for section in section_list:
        scripts = ''.join([scripts, get_hide_section_script(section)])
    return scripts

def get_top_level_header(input_filename):
    common_scripts = get_common_scripts()
    sections = ['msgu_fw_log', 'msgu_hwa_reg', 'msgu_hqa_reg', 'msgu_lba_lbb_mem']
    hide_sec_scripts = get_hide_section_scripts(sections)
    click_link = ''
    for section in sections:
        template = '<p style="color:green;">Click to get <a href="#{}">{}</a></p>'\
        .format(section, (section.replace('_', ' ')).upper())
        click_link = ''.join([click_link,template])
    return \
'''<!DOCTYPE html>
<html lang="en">
<head>
  <title>MSGU Crash Dump Decode</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
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
<a id="top_section"><p style="color:red;">Decoded MSGU log from crash dump:</p></a> 
<p style="color:red;">%s</p>
%s
<p style="color:red;">Internet Explore may not correctly display the result, consider using a modern browser, such as Microsoft Edge or Google Chrome.</p>
</div>''' % (common_scripts, hide_sec_scripts, input_filename, click_link)

def get_top_level_ending():
     return \
'''<footer>
 <p class="copyright">Copyright &copy; 2017 Microsemi Corporation. All rights reserved.</p>
</footer>
</body>
</html>'''

def get_fw_group_header():
    return \
'''<div class="container" id="msgu_fw_log">
<h3 id="msgu_fw_log_title">MSGU FW Log</h3>
</div>
<div class="container" id="msgu_fw_log_main">
<a href="#top_section">Back To Top</a>
<p><span>The following text is decoded from MSGU FW Log section:</span></p>\n'''

def get_fw_group_ending():
    return \
'''<p id="end_msgu_fw_log"><span>End of <a href="#msgu_fw_log">MSGU FW Log</a> section.</a></span></p>
</div>\n'''

def get_hwa_group_header(): 
    return \
'''<div class="container" id="msgu_hwa_reg">
  <h3 id="msgu_hwa_reg_title">MSGU HWA Reg</h3>
</div>
<div class="container" id="msgu_hwa_reg_main">
  <a href="#top_section">Back To Top</a>
  <p><span>The following table contains decoded register dump from MSGU HWA register section:</span></p>\n'''

def get_hwa_group_ending(): 
    return \
'''
  <p id="end_msgu_hwa_reg"><span>End of <a href="#msgu_hwa_reg">MSGU HWA Reg</a> section.</span></p>
  <a href="#top_section">Back To Top</a>
  </div>\n'''

def get_hqa_group_header(queue_list, first_enabled_q):
    hqa_hide_tbl_script = get_hqa_hide_tbl_script(first_enabled_q)
    hqa_nav_tab = get_hqa_nav_tab(queue_list)
    return \
'''  %s
  <div class="container" id="msgu_hqa_reg">
  <h3 id="msgu_hqa_reg_title">MSGU HQA Reg</h3>
  </div>
  <div class="container" id="msgu_hqa_reg_main">
  <div class="container">
  <a href="#top_section">Back To Top</a>
  <p style="color:red;">Click on a tab to select a Q, <span style="color:green;"><b>Green Qs</b></span> are enabled, <span style="color:grey;"><b>GREY Qs</b></span> are disabled.</p>
  %s
  </div>''' % (hqa_hide_tbl_script, hqa_nav_tab)

def get_hqa_group_ending(): 
    return \
''' <div class="container">
  <p id="end_msgu_hqa_reg"><span>End of <a href="#msgu_hqa_reg">MSGU HQA Reg</a> section.</span></p>
  <a href="#top_section">Back To Top</a>
  </div>
  </div>'''

def get_lba_lbb_group_header(): 
    return \
'''<div class="container" id="msgu_lba_lbb_mem">
  <h3 id="msgu_lba_lbb_mem_title">MSGU LBA LBB MEM</h3>
</div>
<div class="container" id="msgu_lba_lbb_mem_main">
  <a href="#top_section">Back To Top</a>
  <p><span>The following IU info is from MSGU LBA and LBB memory dump:</span></p>\n'''

def get_lba_lbb_group_ending(): 
    return \
'''
  <p id="end_msgu_lba_lbb_mem"><span>End of <a href="#msgu_lba_lbb_mem">MSGU LBA LBB</a> section.</span></p>
  <a href="#top_section">Back To Top</a>
  </div>\n'''
