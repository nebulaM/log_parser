import sys
import os
sys.path.append(os.path.dirname(sys.argv[0]))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.msgu import *

if __name__ == '__main__':
    msgu_common.MSGULog().set_input_params()
    if msgu_common.MSGULog().DEBUG_MODE is True:
        standalone = True
    else:
        standalone = False
        fd = open(msgu_common.MSGULog().common_out_filename, 'w')
        fd.write(msgu_html.get_top_level_header(msgu_common.MSGULog().INPUT_DIR))
        fd.close()

    logs = []
    logs.append(msgu_fw_log.FWLog())
    logs.append(msgu_hwa_log.HWALog())
    logs.append(msgu_hqa_log.HQALog())
    logs.append(msgu_lba_lbb_log.LBALBBLog())
    print '======================================'
    for log_module in logs:
        log_module.run(standalone)
        print '======================================'

    if standalone is False:
        fd = open(msgu_common.MSGULog().common_out_filename, 'a')
        fd.write(msgu_html.get_top_level_ending())
        fd.close()
        print 'result is saved in ' + msgu_common.MSGULog().common_out_filename
        print '======================================'

    print 'Please use a modern browser(other than Internet Explore) to view the result if possible.\n'
    print 'If you view the result through Internet Explore, Javascript can be blocked by default.'
    print 'A dialog box saying "Internet Explore restricts this webpage from running scripts or ActiveX controls" may appear at bottom of the webpage.'
    print 'If this is the case, then please click the button saying "Allow blocked content" on that dialog box.'
