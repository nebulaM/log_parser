import os
from src.msgu import *
from ..shared import dutil as ut

def run():
    found_log_flag = False

    msgu_common.MSGULog().set_input_params()
    out_filename = ut.get_parsed_filename(msgu_common.MSGULog().INPUT_DIR, msgu_common.MSGULog().MODULE) + '.html'
    out_filename = os.path.join(msgu_common.MSGULog().OUTPUT_DIR, out_filename)

    if msgu_common.MSGULog().DEBUG_MODE:
        standalone = True
    else:
        standalone = False
        with open(out_filename, 'w') as fd:
            fd.write(msgu_html.get_top_level_header(msgu_common.MSGULog().INPUT_DIR))

    logs = []
    logs.append(msgu_fw_log.FWLog())
    logs.append(msgu_hwa_log.HWALog())
    logs.append(msgu_hqa_log.HQALog())
    logs.append(msgu_lba_lbb_log.LBALBBLog())
    print('======================================')
    for log_module in logs:
        if log_module.run(standalone):
            found_log_flag = True
        print('======================================')

    if found_log_flag:
        if not standalone:
            with open(out_filename, 'a') as fd:
                fd.write(msgu_html.get_top_level_ending())
            print('result is saved in ' + out_filename)
            print('======================================')
    else:
        if not standalone:
            os.remove(out_filename)
    return found_log_flag
