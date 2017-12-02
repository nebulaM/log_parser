import os
import sys
import re
import src.msgu.msgu_common as cm
import src.msgu.msgu_html as mhtml
from ..shared import dutil as ut
sys.path.append(os.path.dirname(sys.argv[0]))

class FWLog(cm.MSGULog):
    # name of this object
    SECTION = 'fw_log'
    #DEFINITION_FILE_DIR = os.path.join(os.getcwd(), '..', '..', '..' 'msgux', 'pqi', 'src', 'msgu_log.h')
    DEFINITION_FILE_DIR = os.path.join(cm.MSGULog.INCLUDE_DIR, 'doc', 'msgu', 'msgu_log.h')
    LOG_HEADER = '# MSGU FW Log from DQ location'
    LOG_ENDING = '# HQA Memory'
    # special word on first line of MSGU FW log
    LOG_FIRST_LINE_WORD_1 = 'a0a1a2a3'
    LOG_FIRST_LINE_WORD_8 = 'a4a5a6a7'
    # prefix in msgu.h file that shows the entry is for msgu log
    LOG_ENTRY_PREFIX = 'LOG_DATA\( MSGU_LOG_'
   
    LOG_FIRST_WORD_IDX = 4
    
    # 003d at the correct idx tells this line is a msgu fw log
    re_is_fw_log_token = re.compile('^(0x)?(003[dD])([0-9a-fA-F]{4}$)')

    def __init__(self):
        self.log_start_idx = None
        self.clk_freq = None
    @classmethod
    def _process_line(cls, tag, crash_dump_line, definition_list, verbose=False):
        tag = ut.get_debug_tags(tag, cls.MODULE, cls.SECTION, 'process_line')[0]
        log_word_list = crash_dump_line.split()
        # remove last element because last element is an extra whitespace after spliting the list
        if log_word_list[-1] is ' ':
            log_word_list.pop()

        if len(log_word_list) < 4:
            print tag + 'log_word_list ' + crash_dump_line + \
            ' too short, return without processing this line'
            return [None, None]
        if len(log_word_list) >= 9 \
            and log_word_list[1] == cls.LOG_FIRST_LINE_WORD_1 \
            and log_word_list[8] == cls.LOG_FIRST_LINE_WORD_8:
            log_start_idx = int(log_word_list[4], 16)
            clk_freq = int(log_word_list[5], 16)
            ut.log(tag + 'translate first line: ' + crash_dump_line + ' in MSGU FW Log:', verbose)
            ut.log(tag + 'start index is ' + str(log_start_idx) + \
            ', clock frequency is ' + str(clk_freq) + 'Hz', verbose)
            return [log_start_idx, clk_freq]
        raw_key = log_word_list[3]
        time_tick = int(log_word_list[1] + log_word_list[2], 16)
        if cls.re_is_fw_log_token.search(raw_key):
            idx = int(raw_key[4:], 16)
            if idx < 0 or idx >= len(definition_list):
                return time_tick, crash_dump_line + ' meaning of the log not found.'
            definition_line = definition_list[idx]
            trans_line = ut.replace_word_in_line_from_logh(log_word_list, \
            cls.LOG_FIRST_WORD_IDX, definition_line)
            if verbose is True:
                print tag + 'translate line before:'
                print tag + crash_dump_line + '\n'
                print tag + 'translate line after:'
                print trans_line + '\n'
            return time_tick, trans_line
        # line is not a valid msgu fw line
        else:
            # log_word_list[0] is register address,
            # so use range [1:-1] to loop over
            # log_word_list[1:end]
            for this_word in log_word_list[1:-1]:
                if '00000000' != this_word: 
                    return time_tick, crash_dump_line + ' is not a valid MSGU FW log.'
            return None, None

    @classmethod
    def write_result(cls, fd, start_idx_msg, clk_freq, time_list, log_list, standalone):
        if standalone is True:
            pre_0 = ''
            pre_1 = ''
        else:
            pre_0 = '<pre>'
            pre_1 = '</pre>'

        if start_idx_msg is not None:
            fd.write(''.join([pre_0, start_idx_msg, pre_1]))

        if clk_freq is None:
            fd.write(''.join([pre_0, 'Clock frequency is unknown, use "tick" as time unit', pre_1, '\n']))
            for time_tick, log in zip(time_list, log_list):
                fd.write(time_tick + ' tick: ' + log + '\n')
        else:
            # divide by 10^6 so clkFreq is in MHz
            frequency = clk_freq/1000000
            fd.write('%sClock frequency is %d MHz%s\n' % (pre_0, frequency, pre_1))
            for time_tick, log in zip(time_list, log_list):
                time_real = time_tick/frequency
                time_print = ut.add_mark_to_word(str(time_real), ',', 3)
                fd.write('%s%s us: %s%s\n' % (pre_0, time_print, log, pre_1))

    def run(self, standalone=True):
        if standalone is True:
            self.set_input_params()
        tag, tag_next_level = ut.get_debug_tags(None, self.MODULE, self.SECTION, 'run')
        print tag + 'parser starts'
        definition_list = ut.create_def_list_from_logh(tag_next_level, self.DEFINITION_FILE_DIR, \
        self.LOG_ENTRY_PREFIX, self.DEBUG_MODE)
        line_list = ut.save_line_to_list(tag_next_level, self.LOG_HEADER, self.LOG_ENDING, \
        self.INPUT_DIR, self.LOG_LINE_LENGTH)
        trans_list_time = []
        trans_list_log = []
        for line in line_list:
            item_1, item_2 = self._process_line(tag_next_level, line, definition_list, self.DEBUG_MODE)
            if item_1 is None or item_2 is None:
                continue
            if type(item_2) is int and type(item_1) is int:
                self.log_start_idx = item_1
                self.clk_freq = item_2
            else:           
                trans_list_time.append(item_1)
                trans_list_log.append(item_2)
        #utils.list_print(trans_list)
        if self.log_start_idx is None or self.log_start_idx > len(trans_list_time):
            if self.log_start_idx is None:
                no_log_start_idx_msg = tag + \
                'Warning, start index not found, not sort the log!\n'
            else:
                no_log_start_idx_msg = tag + \
                'Warning, start index =' + str(self.log_start_idx) + ' too large, not sort the log!\n'
            sorted_trans_list_time = trans_list_time
            sorted_trans_list_log = trans_list_log
        else:
            no_log_start_idx_msg = None
            sorted_trans_list_time = trans_list_time[self.log_start_idx:]
            sorted_trans_list_time.extend(trans_list_time[0:self.log_start_idx])
            sorted_trans_list_log = trans_list_log[self.log_start_idx:]
            sorted_trans_list_log.extend(trans_list_log[0:self.log_start_idx])
        if self.DEBUG_MODE is True:
            print "\nsorted list is:"
            for time_tick, log in zip(sorted_trans_list_time, sorted_trans_list_log):
                time_tick_hex = format(time_tick, '08x')
                print time_tick_hex + ' time: ' + log
            print "\n"
        try:
            os.stat(self.OUTPUT_DIR)
        except:
            os.mkdir(self.OUTPUT_DIR)

        if standalone is True:
            filename = ut.get_parsed_filename(self.INPUT_DIR, self.MODULE, self.SECTION) + '.log'
            filename = os.path.join(self.OUTPUT_DIR, filename)
            fd = open(filename, 'w')

            fd.write('Decoded ' + self.MODULE + self.SECTION + \
            'from crash dump ' + self.INPUT_DIR + ':\n')
            self.write_result(fd, no_log_start_idx_msg, self.clk_freq, \
            sorted_trans_list_time, sorted_trans_list_log, standalone)

            fd.close()
            print tag + 'result saved in ' + filename
        else:
            fd = open(self.common_out_filename, 'a')
            fd.write(mhtml.get_fw_group_header())

            self.write_result(fd, no_log_start_idx_msg, self.clk_freq, \
            sorted_trans_list_time, sorted_trans_list_log, standalone)
      
            fd.write(mhtml.get_fw_group_ending())
            fd.close()

        # set vars read from crash dump back to none after finish
        self.log_start_idx = None
        self.clk_freq = None
        print tag + 'parser ends'

if __name__ == '__main__':
    this = FWLog()
    this.run()
