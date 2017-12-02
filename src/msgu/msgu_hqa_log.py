import os
import sys
import xml.etree.ElementTree as ET
import src.msgu.msgu_common as cm
import src.msgu.msgu_html as mhtml
from ..shared import dutil as ut
from ..shared import struct as REG
sys.path.append(os.path.dirname(sys.argv[0]))

class HQALog(cm.MSGULog, cm.HQA_WORD):
    SECTION = 'hqa_log'
    DEFINITION_FILE_DIR = os.path.join(cm.MSGULog.INCLUDE_DIR, 'doc', 'msgu', 'MSGU_HQA_REG.xml')
    LOG_HEADER = '# HQA Memory'
    LOG_ENDING = '# LBA Memory'

    HQA_ADDRESS_OFFSET = 0x240000
    BYTE_PER_REG = 8
    # Currently, queue config for Wildfire is the same as for Luxor
    # How many queues in total
    LUXOR_Q_NUM = 512
    LUXOR_IB_ADMIN_FIRST_QID = 0
    LUXOR_IB_ADMIN_LAST_QID = 65
    LUXOR_IB_OPER_FIRST_QID = 66
    LUXOR_IB_OPER_LAST_QID = 255
    LUXOR_OB_ADMIN_FIRST_QID = 256
    LUXOR_OB_ADMIN_LAST_QID = 321
    LUXOR_OB_OPER_FIRST_QID = 322
    LUXOR_OB_OPER_LAST_QID = 511
    LUXOR_REG_PER_Q = 128
    WF_Q_NUM = 512
    WF_IB_ADMIN_FIRST_QID = 0
    WF_IB_ADMIN_LAST_QID = 65
    WF_IB_OPER_FIRST_QID = 66
    WF_IB_OPER_LAST_QID = 255
    WF_OB_ADMIN_FIRST_QID = 256
    WF_OB_ADMIN_LAST_QID = 321
    WF_OB_OPER_FIRST_QID = 322
    WF_OB_OPER_LAST_QID = 511
    # How many register per queue
    WF_REG_PER_Q = 128
    # HBA and Raid mode ID
    EGSM_HBA_QID = 28
    EGSM_RAID_QID = 57
    # for int mode
    LOG_CR_HEADER = '# CR - PQI HQA Configuration'
    LOG_CR_ENDING = '# CR - PQI HQA Error Register'
    LOG_CR_LINE_LENGTH = 27
    LOG_CR_ADDRESS = 0xbf607008
    LOG_CR_BYTE_PER_REG = 8
    LOG_CR_VAL_PER_LINE = 2

    def __init__(self):
        self.first_enabled_q = self.DEFAULT_ID
        # Default int mode
        self.hqa_int_mode = self.W_MSIX
        # default Q range, use LUXOR
        self.q_num = self.LUXOR_Q_NUM
        self.qid_first_ib_admin = self.LUXOR_IB_ADMIN_FIRST_QID
        self.qid_last_ib_admin = self.LUXOR_IB_ADMIN_LAST_QID
        self.qid_first_ib_oper = self.LUXOR_IB_OPER_FIRST_QID
        self.qid_last_ib_oper = self.LUXOR_IB_OPER_LAST_QID
        self.qid_first_ob_admin = self.LUXOR_OB_ADMIN_FIRST_QID
        self.qid_last_ob_admin = self.LUXOR_OB_ADMIN_LAST_QID
        self.qid_first_ob_oper = self.LUXOR_OB_OPER_FIRST_QID
        self.qid_last_ob_oper = self.LUXOR_OB_OPER_LAST_QID
        self.q_reg_per_q = self.LUXOR_REG_PER_Q
   
    def set_q_range(self, chipset):
        if chipset == self.LUXOR:
            # default is set in initialization, so just pass here.
            pass
        elif chipset == self.WF:
            self.q_num = self.WF_Q_NUM
            self.qid_first_ib_admin = self.WF_IB_ADMIN_FIRST_QID
            self.qid_last_ib_admin = self.WF_IB_ADMIN_LAST_QID
            self.qid_first_ib_oper = self.WF_IB_OPER_FIRST_QID
            self.qid_last_ib_oper = self.WF_IB_OPER_LAST_QID
            self.qid_first_ob_admin = self.WF_OB_ADMIN_FIRST_QID
            self.qid_last_ob_admin = self.WF_OB_ADMIN_LAST_QID
            self.qid_first_ob_oper = self.WF_OB_OPER_FIRST_QID
            self.qid_last_ob_oper = self.WF_OB_OPER_LAST_QID
            self.q_reg_per_q = self.WF_REG_PER_Q
        else:
            raise ValueError('chipset ' + chipset + 'is not supported.')

    def set_int_mode(self, tag):
        tag_next_level = ut.get_debug_tags(tag, self.MODULE, self.SECTION, 'set_int_mode')[1]
        cr_reg_lines = ut.save_line_to_list(tag_next_level, self.LOG_CR_HEADER, self.LOG_CR_ENDING, \
        self.INPUT_DIR, self.LOG_CR_LINE_LENGTH)
        cr_addr_str = '{:08x}'.format(self.LOG_CR_ADDRESS)
        for line in cr_reg_lines:
            if cr_addr_str in line:
                this_line_list = ut.crash_dump_line_to_addr_val_pair(tag_next_level, line, self.ENDIANNESS, \
                self.LOG_CR_BYTE_PER_REG, self.BYTE_PER_VAL, self.LOG_CR_VAL_PER_LINE)
                for reg_addr, reg_val in this_line_list:
                    if reg_addr == self.LOG_CR_ADDRESS and \
                       ut.bit_shift(reg_val, 32)[0] == 1:
                       self.hqa_int_mode = self.W_INTX
                       break
                break

    def init_queues(self, crash_dump_reg_list, verbose=False):
        queue_list = []
        for qid in range(0, self.q_num):
            if qid >= self.qid_first_ib_admin and qid <= self.qid_last_ib_admin:
                q_mode = self.W_IB
                q_type = self.W_ADMIN
            elif qid >= self.qid_first_ib_oper and qid <= self.qid_last_ib_oper:
                q_mode = self.W_IB
                q_type = self.W_OPER
            elif qid >= self.qid_first_ob_admin and qid <= self.qid_last_ob_admin:
                q_mode = self.W_OB
                q_type = self.W_ADMIN
            elif qid >= self.qid_first_ob_oper and qid <= self.qid_last_ob_oper:
                q_mode = self.W_OB
                q_type = self.W_OPER
            else:
                q_mode = self.W_NA
                q_type = self.W_NA
                continue
            offset = qid * self.q_reg_per_q
            this_q = HQA_Q(qid, q_mode, q_type, offset, self.hqa_int_mode)
            # Special reg_addr
            gen_cfg_reg_addr = 0x0038 + offset
            hwa_cfg_reg_addr = 0x0040 + offset
            hqa_eng_cfg_reg_addr = 0x0048 + offset
            error_reg_addr  = 0x0060 + offset
        
            # lower bound is 0+offset
            this_q.reg_lower_bound = offset
            this_q.reg_upper_bound = self.q_reg_per_q + offset - self.BYTE_PER_REG

            for reg_addr, reg_val in crash_dump_reg_list:
                reg_addr -= (self.MSGU_ADDRESS_OFFSET + self.HQA_ADDRESS_OFFSET)
                if reg_addr < this_q.reg_lower_bound:
                    continue
                if reg_addr > this_q.reg_upper_bound:
                    #print qid,' break at ', reg_addr
                    break
                this_q.decoded_reg_dict[reg_addr] = REG.DecodedReg(reg_addr, 'TBD', reg_val)
                if reg_addr == gen_cfg_reg_addr:
                    if ut.bit_shift(reg_val, 30)[0] == 1:
                        this_q.status_dict['rearm'] = self.W_ON
                    if ut.bit_shift(reg_val, 29)[0] == 1:
                        this_q.is_enabled = True
                        if self.first_enabled_q < 0:
                            self.first_enabled_q = this_q.qid
                            if verbose is True:
                                print 'first enabled Q is ', self.first_enabled_q

                elif reg_addr == hwa_cfg_reg_addr and \
                    this_q.q_mode is self.W_IB and \
                    this_q.q_type is self.W_OPER:
                    egsm_id = ut.bit_shift(reg_val, '40:32')[0]
                    if egsm_id == self.EGSM_HBA_QID:
                        this_q.status_ib_oper_q_raid_hba = self.W_HBA
                    elif egsm_id == self.EGSM_RAID_QID:
                        this_q.status_ib_oper_q_raid_hba = self.W_RAID
                    del egsm_id

                elif reg_addr == hqa_eng_cfg_reg_addr:
                    if this_q.q_mode is self.W_OB and \
                       this_q.q_type is self.W_OPER:
                        this_q.status_ob_oper_q_int_num = ut.bit_shift(reg_val, '55:48')[0]

                    if ut.bit_shift(reg_val, 63)[0] == 1:
                        this_q.status_dict['int_max_tmr'] = self.W_ENABLE
                    if ut.bit_shift(reg_val, 62)[0] == 1:
                        this_q.status_dict['int_min_tmr'] = self.W_ENABLE
                    
                    if ut.bit_shift(reg_val, 31)[0] == 1:
                        this_q.status_dict['idx_max_tmr'] = self.W_ENABLE
                    if ut.bit_shift(reg_val, 30)[0] == 1:
                        this_q.status_dict['idx_min_tmr'] = self.W_ENABLE

                    if ut.bit_shift(reg_val, 15)[0] == 1:
                        this_q.status_dict['iu_max_tmr'] = self.W_ENABLE

                    if ut.bit_shift(reg_val, 14)[0] == 1:
                        this_q.status_dict['iu_min_tmr'] = self.W_ENABLE
                elif reg_addr == error_reg_addr:
                    if ut.bit_shift(reg_val, 0)[0] == 1:
                        this_q.is_bad_q = True
            queue_list.append(this_q)
            if verbose is True:
                print 'qid %d\n%s %s\nlower: %s\nupper: %s' % \
                (this_q.qid, this_q.q_mode, this_q.q_type, \
                '{:08x}'.format(this_q.reg_lower_bound), \
                '{:08x}'.format(this_q.reg_upper_bound))
            del this_q
        return queue_list

    @classmethod
    def get_reg_meaning(cls, tag, queue_list, verbose=False):
        tag, tag_next_level = ut.get_debug_tags(tag, cls.MODULE, cls.SECTION, 'get_reg_meaning')
        tree = ET.parse(cls.DEFINITION_FILE_DIR)
        root = tree.getroot()
        for idx, hqa_q in enumerate(queue_list):
            if hqa_q.is_enabled is False:
                continue
            if verbose is True:
                print 'qid ', hqa_q.qid
            for hqa_reg_addr, decoded_reg in hqa_q.decoded_reg_dict.iteritems():
                doc_addr = hqa_reg_addr - hqa_q.addr_offset
                for reg in root.findall('register'):
                    if doc_addr == int(reg.find('reg_address').text, 16):
                        decoded_reg.reg_name = reg.find('reg_name').text
                        if verbose is True:
                            print doc_addr
                            print decoded_reg.reg_name
                        reg_bits = reg.find('reg_bits')
                        if reg_bits is not None:
                            for reg_bit in reg_bits.findall('reg_bit'):
                                bit_pos = reg_bit.find('bit_position').text
                                bit_name = reg_bit.find('bit_name').text
                                bit_des = reg_bit.find('bit_description')
                                bit_meaning = ''
                                if bit_des is not None:
                                    for p in bit_des:
                                        flag_save_this_p = True
                                        if p.attrib:
                                            for p_key, p_val in p.attrib.iteritems():
                                                if hqa_q.status_dict[p_key] != p_val:
                                                    flag_save_this_p = False
                                                    break
                                        if flag_save_this_p is True:
                                            '''
                                                add '\n' to split lines, this is useful to
                                                split meanings with 'When set to logic'
                                            '''
                                            bit_meaning = ''.join([bit_meaning, p.text, '\n'])
                                bit_val, bit_val_str = ut.bit_shift(decoded_reg.reg_val, bit_pos)
                                if cls.re_logic.search(bit_meaning) is not None:
                                    bit_meaning = ut.handle_logic_token(bit_val_str, bit_meaning)
                                if cls.re_hex_token.search(bit_meaning) is not None:
                                    hex_digit = len(bit_val_str) >> 2
                                    if (len(bit_val_str) % 4) != 0:
                                        hex_digit += 1
                                    hex_format = ''.join(['0x{:0', str(hex_digit), 'x}'])
                                bit_meaning = cls.re_hex_token.sub(hex_format.format(bit_val), bit_meaning)
                                bit_meaning = cls.re_dec_token.sub(str(bit_val), bit_meaning)
                                if verbose is True:
                                    print bit_pos
                                    print bit_name
                                    print bit_val_str
                                    print bit_meaning
                                decoded_reg.add_bit_des(bit_pos, bit_name, bit_val_str, bit_meaning)
                hqa_q.decoded_reg_dict[hqa_reg_addr] = decoded_reg
            ut.handle_parse_math_token(tag_next_level, hqa_q.decoded_reg_dict)
            queue_list[idx] = hqa_q
        return queue_list

    @classmethod
    def save_result(cls, tag, queue_list, first_enabled_q, standalone):
        if standalone is True:
            filename = ut.get_parsed_filename(cls.INPUT_DIR, cls.MODULE, cls.SECTION) + '.html'
            filename = os.path.join(cls.OUTPUT_DIR, filename)
            fd = open(filename, 'w')
            fd.write(mhtml.get_hqa_standalone_header(cls.INPUT_DIR, queue_list, first_enabled_q))
            for queue in queue_list:
                if queue.is_enabled is True:
                    # use address in doc when save
                    for reg_addr in queue.decoded_reg_dict.iterkeys():
                        queue.decoded_reg_dict[reg_addr].reg_address += cls.HQA_ADDRESS_OFFSET 
                    fd.write(mhtml.get_hqa_tbl_header(queue, first_enabled_q))
                    ut.save_decoded_reg_dict_to_html_table(queue.decoded_reg_dict, fd, True)
                    fd.write(mhtml.get_hqa_tbl_ending())
            fd.write(mhtml.get_hqa_standalone_ending())
            fd.close()
            print tag + 'result saved in ' + filename
        else:
            fd = open(cls.common_out_filename, 'a')
            fd.write(mhtml.get_hqa_group_header(queue_list, first_enabled_q))
            for queue in queue_list:
                if queue.is_enabled is True:
                    # use address in doc when save
                    for reg_addr in queue.decoded_reg_dict.iterkeys():
                        queue.decoded_reg_dict[reg_addr].reg_address += cls.HQA_ADDRESS_OFFSET 
                    fd.write(mhtml.get_hqa_tbl_header(queue, first_enabled_q))
                    ut.save_decoded_reg_dict_to_html_table(queue.decoded_reg_dict, fd, cls.DEBUG_MODE)
                    fd.write(mhtml.get_hqa_tbl_ending())
            fd.write(mhtml.get_hqa_group_ending())
            fd.close()

    def run(self, standalone=True):
        if standalone is True:
            self.set_input_params()
        self.set_chipset()
        self.set_q_range(self.chipset)
        
        tag, tag_next_level = ut.get_debug_tags(None, self.MODULE, self.SECTION, 'run')
        print tag + 'parser starts'
        self.set_int_mode(tag_next_level)
        crash_dump_reg_list = self.get_reg_val_list(tag_next_level, self.LOG_HEADER, self.LOG_ENDING, self.BYTE_PER_REG)
        
        queue_list = self.init_queues(crash_dump_reg_list, self.DEBUG_MODE)
        queue_list = self.get_reg_meaning(tag_next_level, queue_list, self.DEBUG_MODE)

        self.save_result(tag_next_level, queue_list, self.first_enabled_q, standalone)

        print tag + 'parser ends'

class HQA_Q(cm.HQA_WORD):
    def __init__(self, qid, q_mode, q_type, addr_offset, hqa_int_mode):
        # id of the queue, starting from 0
        self.qid = qid
        # IB or OB
        self.q_mode = q_mode
        # Oper or Admin
        self.q_type = q_type
        # register offset in this queue
        self.addr_offset = addr_offset

        # boundary of regs belong to this queue in HQA reg dump
        # necessary to have because HQA reg dump dumps reg 
        # for all queues without any identifier
        self.reg_lower_bound = 0
        self.reg_upper_bound = 0        

        # is this queue enabled
        self.is_enabled = False
        # is this queue contains error
        self.is_bad_q = False
        # raid/hba only for IB OPER Q
        self.status_ib_oper_q_raid_hba = self.W_NA
        # int num only for OB OPER Q
        self.status_ob_oper_q_int_num = self.DEFAULT_ID
        self.status_dict = {}
        self.status_dict['mode'] = self.q_mode
        self.status_dict['type'] = self.q_type
        self.status_dict['op'] = self.status_ib_oper_q_raid_hba
        self.status_dict['int'] = hqa_int_mode
        self.status_dict['idx_max_tmr'] = self.W_DISABLE
        self.status_dict['idx_min_tmr'] = self.W_DISABLE
        # iu timers only for OPER Q
        self.status_dict['iu_max_tmr'] = self.W_DISABLE
        self.status_dict['iu_min_tmr'] = self.W_DISABLE
        # int timers only for OB Q
        self.status_dict['int_max_tmr'] = self.W_DISABLE
        self.status_dict['int_min_tmr'] = self.W_DISABLE
        self.status_dict['rearm'] = self.W_OFF
        self.decoded_reg_dict = {}

# if entry point is this script, then run this script independently from other parsers.
if __name__ == '__main__':
    this = HQALog()
    this.run()
