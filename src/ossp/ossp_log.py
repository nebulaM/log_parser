import os
import re
import itertools
import collections
import xml.etree.ElementTree as ET
import src.ossp.ossp_html as ohtml
from ..shared import dutil as ut
from ..shared import struct as REG

class OSSPLog(ut.XMLREToken):
    MODULE = 'ossp'
    SECTION = 'reg_dump'

    # path to register definition in xml, from PD
    # TODO: better way to define files is TBD
    DEF_FILE_DIR_HSST_GLB   = os.path.join(ut.DumpArgvWorker().INCLUDE_DIR, 'doc', 'ossp', 'pm88_60_233global_bd_reg.xml')
    DEF_FILE_DIR_HSST_XPORT = os.path.join(ut.DumpArgvWorker().INCLUDE_DIR, 'doc', 'ossp', 'pm88_60_233_bd_reg.xml')
    DEF_FILE_DIR_SSPA       = os.path.join(ut.DumpArgvWorker().INCLUDE_DIR, 'doc', 'ossp', 'pm88_60_232_bd_reg.xml')
    DEF_FILE_DIR_SSPL       = os.path.join(ut.DumpArgvWorker().INCLUDE_DIR, 'doc', 'ossp', 'pm88_60_236_bd_reg.xml')

    # log headers for each section in BC dump
    LOG_HEADER_HSST_GLB   = 'HSST Global Registers'
    LOG_HEADER_HSST_XPORT = 'HSST Transport Registers'
    ''' TODO: for SSPA can we remove this extra column(':') in sas_debug.c?'''
    LOG_HEADER_SSPA       = 'SSPA Registers:'
    LOG_HEADER_SSPL       = 'SSPL (12G) Registers'
    # log ending, currently all SAS reg dump sections use the following line
    LOG_ENDING = '======================================================='

    # common line length in SAS reg dump, some SAS reg dump sections have
    # a different line length, override this param if that is the case
    LOG_LINE_LENGTH_COMMON = 78

    # max OSSP is 4 on HD card, feel free to increase the number when needed 
    # without touch the code in this script
    MAX_NUM_OSSP = 4

    # byte per register
    BYTE_PER_REG = 8

    # by default assume 8 PHYs per OSSP, if this script cannot dynamically read PHY count
    # from a section, then it assumes DEFAULT_PHY_COUNT on that OSSP
    DEFAULT_PHY_COUNT = 8

    @classmethod
    def _get_def_reg_dict(cls, xml_filename, debug=False):
        ''' Get register def from xml file
            @param xml_filename: name of xml file
            @param debug: optional, True to print out addition log
            @return reg_dict: dict of def register in DefReg struct
        '''
        tree = ET.parse(xml_filename)
        root = tree.getroot()
        reg_dict = {}
        for reg in root.findall('register'):
            reg_name = reg.find('reg_name').text
            reg_addr = int(reg.find('reg_address').text, 16)
            #print(reg_name)
            #print(reg_addr)
            this_reg = REG.DefReg(reg_addr, reg_name)
            reg_bits = reg.find('reg_bits')
            if reg_bits is not None:
                for reg_bit in reg_bits.findall('reg_bit'):
                    bit_pos = reg_bit.find('bit_position').text
                    bit_name = reg_bit.find('bit_name').text
                    bit_des = reg_bit.find('bit_description')
                    bit_meaning = ''
                    if bit_des is not None:
                        for p in bit_des:
                            '''
                                add '\n' to split lines, this is useful to
                                split meanings with 'When set to logic'
                            '''
                            if p.text is not None:
                                bit_meaning = ''.join([bit_meaning, p.text, '\n'])
                    #print(bit_pos)
                    #print(bit_name)
                    #print(bit_meaning)
                    this_reg.add_bit_des(bit_pos, bit_name, bit_meaning)
            reg_dict[reg_addr] = this_reg
        if debug is True:
            for reg_addr in reg_dict.keys():
                reg = reg_dict[reg_addr]
                print(reg.reg_address)
                print(reg.reg_name)
                if reg.has_bit_des is True:
                    bit_dict = reg.bit_dict
                    for key in bit_dict.keys():
                        print(key)
                        print(bit_dict[key])
        return reg_dict

    @classmethod
    def _get_reg_meaning(cls, tag, dump_reg_list, def_reg_dict, debug=False):
        ''' Explain register meaning in dump_reg_list based on def_reg_dict
            @param tag
            @param dump_reg_list: list of reg_addr, reg_val pairs read from dump file
            @param def_reg_dict: dict[reg_addr] = REG.DefReg where reg_addr is in decimal
            @return decoded_reg_dict: dict[reg_addr] = REG.DecodedReg where reg_addr is in decimal
        '''
        tag = ut.get_debug_tags(tag, cls.MODULE, cls.SECTION, '_get_reg_meaning')[0]
        decoded_reg_dict = {}
        for reg_addr, reg_val in dump_reg_list:
            if reg_addr in def_reg_dict:
                reg = def_reg_dict[reg_addr]
                decoded_reg = REG.DecodedReg(reg_addr, reg.reg_name, reg_val)
                if debug is True:
                    print(hex(decoded_reg.reg_address))
                    print(decoded_reg.reg_name)

                if reg.has_bit_des is True:
                    for bit_pos in reg.bit_dict.keys():
                        bit_name, raw_bit_meaning = reg.bit_dict[bit_pos]
                        bit_val, bit_val_str = ut.bit_shift(reg_val, bit_pos)
                        bit_meaning = raw_bit_meaning

                        if cls.re_logic.search(bit_meaning) is not None:
                            bit_meaning = ut.handle_logic_token(bit_val_str, bit_meaning)
                        if cls.re_hex_token.search(bit_meaning) is not None:
                            hex_digit = len(bit_val_str) >> 2
                            if (len(bit_val_str) % 4) != 0:
                                hex_digit += 1
                            hex_format = ''.join(['0x{:0', str(hex_digit), 'x}'])
                            bit_meaning = cls.re_hex_token.sub(hex_format.format(bit_val), bit_meaning)
                        bit_meaning = cls.re_dec_token.sub(str(bit_val), bit_meaning)
                        if debug is True:
                            print(bit_pos)
                            print(bit_val_str)
                            print(bit_meaning)
                        # add bit_val_str instead of bit_val
                        decoded_reg.add_bit_des(bit_pos, bit_name, bit_val_str, bit_meaning)
                decoded_reg_dict[decoded_reg.reg_address] = decoded_reg
        if not decoded_reg_dict:
            print(tag + 'Warnning, empty decoded reg dict')
        # comment out as math token not used in SAS xml for now
        '''else:
            ut.handle_parse_math_token(tag_next_level, decoded_reg_dict)'''
        return decoded_reg_dict

    @classmethod
    def _get_ossp_phy_list(cls, tag, log_header, dump_file):
        ''' Get OSSP-PHY list from dump file
            @param tag
            @param log_header: header of the log in dump file
            @param dump_file: input dump file
            @return ossp_phy_list: list of [ossp_id, phy_list], where phy_list is list of phy
        '''
        tag = ut.get_debug_tags(tag, cls.MODULE, log_header, '_get_ossp_phy_list')[0]
        ossp_phy_list = []
        total_phy_count = 0
        for ossp_id in range(cls.MAX_NUM_OSSP):
            header = log_header + ' (OSSP_%d):' % (ossp_id)
            found_header = False
            phy_count = 0
            for line in dump_file:
                if found_header is True:
                    phy_count = line.count('PHY')
                    if phy_count <= 0:
                        phy_count = line.count('phy')
                    break
                if line == header:
                    found_header = True

            # this OSSP/reg dump not in file
            if found_header is False:
                continue

            if phy_count <= 0:
                print(tag + 'Warning, PHY count not found for OSSP %d, use default PHY count = %d for this OSSP' % \
                (ossp_id, cls.DEFAULT_PHY_COUNT))
                phy_count = cls.DEFAULT_PHY_COUNT

            this_phy_list = []
            for phy_id in range(total_phy_count, phy_count+total_phy_count):
                #print(phy_id)
                this_phy_list.append(phy_id)
            ossp_phy_list.append([ossp_id, this_phy_list])
            # now all phys for current OSSP is translated, update total PHY count before moving to next OSSP
            total_phy_count += phy_count
        return ossp_phy_list

    @classmethod
    def _decode_per_ossp_reg_dump(cls, tag, log_header, dump_file, \
    def_reg_dict, fd, line_len = LOG_LINE_LENGTH_COMMON, target_list=[], debug=False):
        ''' Decode per OSSP register dump in OSSP section
            @param tag
            @param log_header: header of the log in dump file
            @param dump_file: input dump file
            @param  def_reg_dict: definition reg dict
            @output fd: fd to output file
            @param target_list: Optional, only translate regs in target list if given
            @param line_len: Optional, line length in this section
            @note: fd contains dump for the corresponding reg section after this function being called 
        '''
        tag, tag_next_level = ut.get_debug_tags(tag, cls.MODULE, log_header, '_decode_per_ossp_reg_dump')
        ossp_reg_dump_dict = {}
        ossp_count = 0
        found_log_flag = False
        for ossp_id in range(cls.MAX_NUM_OSSP):
            header = log_header + ' (OSSP_%d):' % (ossp_id)
            re_line_token = re.compile('(0x[0-9a-fA-F]{3}:)((\s[0-9a-fA-F]{%d}){%d})' % (cls.BYTE_PER_REG, 1))
            lines = ut.save_line_to_list(tag_next_level, header, cls.LOG_ENDING, \
            'DUMMY', line_len, False, dump_file)
            if lines:
                found_log_flag = True
                ossp_reg_dump_dict[ossp_id] = []
                for line in lines:
                    error = ''
                    if re_line_token.match(line) is None:
                        error = 'Not a valid line'
                    elif ':' in line:
                        addr, val = line.split(':')
                        try:
                            addr = int(addr, 16)
                            if target_list:
                                if addr not in target_list:
                                    continue
                            val = int(val, 16)
                            ossp_reg_dump_dict[ossp_id].append([addr, val])
                            #print(line)
                        except ValueError:
                            error = 'ValuleError'
                    else:
                        error = 'Missing ":" in line '
                    if error:
                        print(tag + 'Warning, [%s] cannot translate line: %s' %(error, line))
                ossp_count += 1

        if found_log_flag is False:
            return found_log_flag
        # filter out common registers
        # bypass if we only have 1 ossp
        common_reg_list = []
        if ossp_count > 1:
            unique_reg_addr_set = set()
            # if we have more than one OSSP for this register dump, find out reg with unique value
            if ossp_count > 0:
                unique_reg_addr_set = ut.find_unique_reg(ossp_reg_dump_dict)
            else:
                print(tag + 'Warning, no OSSP found for this register dump''')
            common_reg_saved_flag = False
            for id in range(cls.MAX_NUM_OSSP):
                try:
                    dump_reg_list = ossp_reg_dump_dict[id]
                    if common_reg_saved_flag is False:
                        common_reg_list = filter(lambda reg: reg[0] not in unique_reg_addr_set, dump_reg_list)
                        common_reg_saved_flag = True
                    ossp_reg_dump_dict[id] = filter(lambda reg: reg[0] in unique_reg_addr_set, dump_reg_list)
                except KeyError:
                    pass
        
        fd.write(ohtml.get_section_header(log_header))
        first_ossp_id = -1
        for ossp_id in range(cls.MAX_NUM_OSSP):
            try:
                dump_reg_list = ossp_reg_dump_dict[ossp_id]
                #print(dump_reg_list)
                if first_ossp_id == -1:
                    first_ossp_id = ossp_id
                decoded_reg_dict = cls._get_reg_meaning(tag_next_level, dump_reg_list, def_reg_dict, debug)
                fd.write(ohtml.get_per_ossp_tbl_header(log_header, ossp_id, first_ossp_id))
                ut.save_reg_dump_to_html(dump_reg_list, 0, 1, fd)
                ut.save_decoded_reg_dict_to_html_table(decoded_reg_dict, fd, debug)
                fd.write(ohtml.get_tbl_ending())
            except KeyError:
                pass
        if common_reg_list:
            fd.write(ohtml.get_common_reg_header(log_header))
            decoded_reg_dict = cls._get_reg_meaning(tag_next_level, common_reg_list, def_reg_dict, debug)
            ut.save_reg_dump_to_html(common_reg_list, 0, 1, fd)
            ut.save_decoded_reg_dict_to_html_table(decoded_reg_dict, fd, debug)
        # finally write section ending
        fd.write(ohtml.get_section_ending(log_header))
        return found_log_flag

    @classmethod
    def _decode_per_phy_reg_dump(cls, tag, log_header, dump_file, \
    def_reg_dict, fd, line_len = LOG_LINE_LENGTH_COMMON, target_list=[], debug=False):
        ''' Decode per PHY register dump in OSSP section
            @param tag
            @param log_header: header of the log in dump file
            @param dump_file: input dump file
            @param  def_reg_dict: definition reg dict
            @output fd: fd to output file
            @param target_list: Optional, only translate regs in target list if given
            @param line_len: Optional, line length in this section
            @note: fd contains dump for the corresponding reg section after this function being called 
        '''
        tag, tag_next_level = ut.get_debug_tags(tag, cls.MODULE, log_header, '_decode_per_phy_reg_dump')
        found_log_flag = False
        ossp_phy_list = []
        total_phy_count = 0
        phy_reg_dump_dict = {}
        for ossp_id in range(cls.MAX_NUM_OSSP):
            header = log_header + ' (OSSP_%d):' % (ossp_id)
            found_header = False
            phy_count = 0
            for line in dump_file:
                if found_header is True:
                    phy_count = line.count('PHY')
                    if phy_count <= 0:
                        phy_count = line.count('phy')
                    if phy_count > 0:
                        line_len = 6 + phy_count*(cls.BYTE_PER_REG + 1)
                    print(tag + 'OSSP %d has line length %d' % (ossp_id, line_len))
                    break
                if line == header:
                    found_header = True

            # this OSSP/reg dump not in file
            if found_header is False:
                continue

            if phy_count <= 0:
                print(tag + 'Warning, PHY count not found for OSSP %d, assume default PHY count = %d from this OSSP' % (ossp_id, cls.DEFAULT_PHY_COUNT))
                phy_count = cls.DEFAULT_PHY_COUNT

            re_line_token = re.compile('(0x[0-9a-fA-F]{3}:)((\s[0-9a-fA-F]{%d}){%d})' % (cls.BYTE_PER_REG, phy_count))
            lines = ut.save_line_to_list(tag_next_level, header, cls.LOG_ENDING, \
            'DUMMY', line_len, False, dump_file)
            if lines:
                found_log_flag = True
                this_phy_list = []
                for phy_id in range(total_phy_count, phy_count+total_phy_count):
                    #print(phy_id)
                    this_phy_list.append(phy_id)
                    phy_reg_dump_dict[phy_id] = []
                ossp_phy_list.append([ossp_id, this_phy_list])
                for line in lines:
                    error = ''
                    if re_line_token.match(line) is None:
                        error = 'Not a valid line'
                    elif ':' in line:
                        addr, val_from_all_phy = line.split(':')
                        try:
                            addr = int(addr ,16)
                            if target_list:
                                if addr not in target_list:
                                    continue
                            val_list = [int(x, 16) for x in val_from_all_phy.split()]
                            for phy_id in range(total_phy_count, phy_count+total_phy_count):
                                phy_reg_dump_dict[phy_id].append([addr, val_list[phy_id-total_phy_count]])
                            #print(line)
                        except ValueError:
                            error = 'ValuleError'
                    else:
                        error = 'Missing ":" in line '
                    if error:
                        print('%sWarning, [%s] cannot translate line: %s' %(tag, error, line))
                # now all phys for current OSSP is translated, update total PHY count
                # before moving to next OSSP
                total_phy_count += phy_count

        if found_log_flag is False:
            return found_log_flag
        
        # sanity check
        for phy_id in range(total_phy_count):
            if phy_id not in phy_reg_dump_dict:
                print(tag + 'Warning, reg list for for PHY %d not found' %(phy_id))

        # filter out common registers
        unique_reg_addr_set = set()
        # if we have more than one PHY, find out reg with unique value
        if total_phy_count > 0:
            unique_reg_addr_set = ut.find_unique_reg(phy_reg_dump_dict)
        else:
            print(tag + 'Warning, no PHY found''')
        common_reg_list = []
        common_reg_saved_flag = False
        for phy_id in range(total_phy_count):
            try:
                dump_reg_list = phy_reg_dump_dict[phy_id]
                if common_reg_saved_flag is False:
                    common_reg_list = filter(lambda reg: reg[0] not in unique_reg_addr_set, dump_reg_list)
                    common_reg_saved_flag = True
                phy_reg_dump_dict[phy_id] = filter(lambda reg: reg[0] in unique_reg_addr_set, dump_reg_list)
            except KeyError:
                pass
        if ossp_phy_list:
            first_phy_id = ossp_phy_list[0][1][0]
            fd.write(ohtml.get_section_header(log_header))
            for ossp_id, phy_list in ossp_phy_list:
                for phy_id in phy_list:
                    try:
                        dump_reg_list = phy_reg_dump_dict[phy_id]
                        #print(dump_reg_list)
                        decoded_reg_dict = cls._get_reg_meaning(tag_next_level, dump_reg_list, def_reg_dict, debug)
                        fd.write(ohtml.get_per_phy_tbl_header(log_header, ossp_id, phy_id, first_phy_id))
                        ut.save_reg_dump_to_html(dump_reg_list, 0, 1, fd)
                        ut.save_decoded_reg_dict_to_html_table(decoded_reg_dict, fd, debug)
                        fd.write(ohtml.get_tbl_ending())
                    except KeyError:
                        pass
            if common_reg_list:
                '''fd.write('<p>Common Register between PHY {} - PHY {} for {}</p>'\
                .format(ossp_phy_list[0][1][0], ossp_phy_list[-1][1][-1], log_header))
                fd.write('<a href="#top_section">Back To Top</a>')'''
                fd.write(ohtml.get_common_reg_header(log_header))
                decoded_reg_dict = cls._get_reg_meaning(tag_next_level, common_reg_list, def_reg_dict, debug)
                ut.save_reg_dump_to_html(common_reg_list, 0, 1, fd)
                ut.save_decoded_reg_dict_to_html_table(decoded_reg_dict, fd, debug)

            fd.write(ohtml.get_section_ending(log_header))
        return found_log_flag

    def run(self):
        ''' Run this parser and save the result in an html file
            @return True if log is found
        '''
        argv = ut.DumpArgvWorker()
        argv.parse()
        in_file = argv.INPUT_DIR
        out_dir = argv.OUTPUT_DIR
        debug = argv.DEBUG_MODE

        tag, tag_next_level = ut.get_debug_tags(None, self.MODULE, self.SECTION, 'run')
        print(tag + 'parser starts')

        '''Update per_ossp and per_phy dicts if a new register section is
           added to OSSP register dump.
        '''

        # Get register definition for per OSSP reg dump
        per_ossp_log_dict = collections.OrderedDict()
        per_ossp_log_dict[self.LOG_HEADER_HSST_GLB] = self._get_def_reg_dict(self.DEF_FILE_DIR_HSST_GLB, debug)

        # Get register definition for per PHY reg dump
        per_phy_log_dict = collections.OrderedDict()
        per_phy_log_dict[self.LOG_HEADER_HSST_XPORT] = self._get_def_reg_dict(self.DEF_FILE_DIR_HSST_XPORT, debug)
        per_phy_log_dict[self.LOG_HEADER_SSPA] = self._get_def_reg_dict(self.DEF_FILE_DIR_SSPA, debug)
        per_phy_log_dict[self.LOG_HEADER_SSPL] = self._get_def_reg_dict(self.DEF_FILE_DIR_SSPL, debug)

        ''' Do NOT modify anything below this line.
        '''

        # get output filename base on input file and output dir
        filename = ut.get_parsed_filename(in_file, self.MODULE, self.SECTION) + '.html'
        filename = os.path.join(out_dir, filename)

        # Main parser logic starts here
        found_log_flag = False

        # 1. read input dump file
        dump_file = ut.get_data_from_file(tag_next_level, in_file)

        # 2. get max ossp_phy_list, this is used by html header
        ossp_phy_list = []
        for log_header, def_reg_dict in per_phy_log_dict.items():
            return_ossp_phy_list = self._get_ossp_phy_list(tag_next_level, log_header, dump_file)
            if ossp_phy_list:
                if return_ossp_phy_list:
                    if ut.llen(return_ossp_phy_list, 1) > ut.llen(ossp_phy_list, 1):
                        ossp_phy_list = return_ossp_phy_list
            else:
                ossp_phy_list = return_ossp_phy_list

        # 3. write html header
        fd = open(filename, 'w')
        fd.write(ohtml.get_top_level_header(in_file, list(per_ossp_log_dict.keys()), \
            list(per_phy_log_dict.keys()), ossp_phy_list))

        # 4. translate per OSSP register dump and write the result in fd
        for log_header, def_reg_dict in per_ossp_log_dict.items():
            if self._decode_per_ossp_reg_dump(tag_next_level, log_header, dump_file, def_reg_dict, fd, 15, debug=debug):
                found_log_flag = True

        # 5. translate per PHY register dump and write the result in fd
        ''' TODO: the following line is a bit hacky, it is here
            to put nav bar at proper position.
            This must be called after ohtml.get_top_level_header is called.
            Otherwise global_phy_nav_tab is just an empty str'''
        fd.write(ohtml.global_phy_nav_tab)
        for log_header, def_reg_dict in per_phy_log_dict.items():
            if self._decode_per_phy_reg_dump(tag_next_level, log_header, dump_file, def_reg_dict, fd, debug=debug):
                found_log_flag = True

        # 6. write html ending
        fd.write(ohtml.get_top_level_ending())
        fd.close()

        if found_log_flag is False:
            os.remove(filename)

        print(tag + 'result is saved in ' + filename)
        if not ossp_phy_list:
            print(tag + 'Warning, ossp_phy_list is empty, result for all per-phy sections might be wrong.')
        print(tag + 'parser ends')
        return found_log_flag

def run():
    this = OSSPLog()
    return this.run()

# if entry point is this script, then run this script independently from other parsers.
if __name__ == '__main__':
    run()
