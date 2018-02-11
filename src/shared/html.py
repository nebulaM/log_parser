import os.path
from datetime import datetime

HTML_LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'include', 'lib', 'html')

def _get_hide_section_script(section):
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

def get_hide_section_scripts(section_list):
    scripts = ''
    for section in section_list:
        scripts = ''.join([scripts, _get_hide_section_script(section)])
    return scripts

def get_hide_tbl_script(name, init_id):
    ''' Generate javascript for hiding element with id
        @param name: name of the section
        @param init_id: id of which element that is shown by default
        @return: tuple of [fcn_name, script] where fcn_name is name of
                  the generated function
        @note: example usage get_hide_tbl_script('hqa', 0) generates fcn
               "show_hqa()" with element of id = hqa0 shown by default
    '''
    if init_id < 0:
        init_id = 0
    var_name = 'last_%s_id' % (name)
    fcn_name = 'show_%s' % (name)
    return fcn_name,'''<script>
    var %s=%d;
    function %s(id) {
        if (%s === id) {
            return;
        }
        $(document.getElementById("%s"+%s)).hide();
        $(document.getElementById("%s"+id)).fadeIn();
        %s=id;
    } 
  </script>''' % (var_name, init_id, fcn_name, var_name, name, var_name, name, var_name)

def get_top_level_ending():
    now = datetime.now()
    return \
'''<footer>
 <p class="copyright">Copyright &copy; {} Microsemi Corporation. All rights reserved.</p>
</footer>
</body>
</html>'''.format(now.year)
