''' Data structures for crash dump parser. '''
import collections

class DefReg(object):
    ''' Save reg info read from def file, do not save bit des if bit name contains 'RESERVED'. '''
    def __init__(self, reg_address, reg_name='N/A'):
        if type(reg_address) is str:
            self.reg_address = int(reg_address, 16)
        else:
            self.reg_address = reg_address
        assert (type(self.reg_address) is int \
        or type(self.reg_address) is long), 'Trying to add a none int/long reg address to def reg'
        self.reg_name = reg_name
        self.has_bit_des = False
    def add_bit_des(self, bit_position, bit_name, bit_meaning):
        if 'RESERVED' in bit_name:
            return
        if self.has_bit_des is False:
            self.bit_dict = collections.OrderedDict()
            self.has_bit_des = True
        self.bit_dict[bit_position] = [bit_name, bit_meaning]

    def get_bit_des(self, bit_position):
        if self.has_bit_des is True:
            if bit_position in self.bit_dict:
                return self.bit_dict[bit_position]
        return None, None

class DecodedReg(object):
    ''' Save reg info for decoded reg '''
    def __init__(self, reg_address, reg_name='N/A', reg_val=0x0):
        if type(reg_address) is str:
            self.reg_address = int(reg_address, 16)
        else:
            self.reg_address = reg_address
        assert (type(self.reg_address) is int \
        or type(self.reg_address) is long), 'Trying to add a none int/long reg address to decoded reg'
        self.reg_name = reg_name
        self.reg_val = reg_val
        self.has_bit_des = False
    def add_bit_des(self, bit_position, bit_name, bit_val, bit_meaning):
        if self.has_bit_des is False:
            self.bit_dict = collections.OrderedDict()
            self.has_bit_des = True
        self.bit_dict[bit_position] = [bit_name, bit_val, bit_meaning]

class DefIU(object):
    # both iu_name and iu_code are strings
    def __init__(self, iu_name, iu_code):
        self.iu_name = iu_name
        if type(iu_code) is str:
            self.iu_code = int(iu_code, 16)
        else:
            self.iu_code = iu_code
        assert (type(self.iu_code) is int or\
        (type(self.iu_code) is long)), 'Trying to add bit des to a none int/long IU code' 
        self.has_reg = False
    def add_reg(self, reg_address):
        if type(reg_address) is str:
            reg_address = int(reg_address, 16)
        if self.has_reg is False:
            self.has_reg = True
            self.reg_dict = collections.OrderedDict()
        self.reg_dict[reg_address] = DefReg(reg_address)
    def add_bit_des(self, reg_address, bit_position, bit_name, bit_meaning):
        if type(reg_address) is str:
            reg_address = int(reg_address, 16)
        assert (type(reg_address) is int \
        or type(reg_address) is long), 'Trying to add bit des to a none int/long reg address'
        assert (self.has_reg is True), 'Trying to add bit des before add reg'
        assert (reg_address in self.reg_dict), 'Trying to add bit des to a reg not in reg dict'
        dummy, old_bit_meaning = self.reg_dict[reg_address].get_bit_des(bit_position)
        if old_bit_meaning is not None:
            bit_meaning = ''.join([old_bit_meaning, '\n', bit_meaning])    
        self.reg_dict[reg_address].add_bit_des(bit_position, bit_name, bit_meaning)
    
    def get_reg(self, reg_address):
        if type(reg_address) is str:
            reg_address = int(reg_address, 16)
        if self.has_reg is True:
            if reg_address in self.reg_dict:
                return self.reg_dict[reg_address]
        return None

class DecodedIU(object):
    def __init__(self, iu_name, iu_code, iu_length, raw_reg_list, reg_dict):
        self.iu_name = iu_name
        if type(iu_code) is str:
            self.iu_code = int(iu_code, 16)
        else:
            self.iu_code = iu_code
        assert (type(self.iu_code) is int or\
        (type(self.iu_code) is long)), 'Trying to add bit des to a none int/long IU code'
        self.iu_length = iu_length
        self.reg_dict = reg_dict
        self.raw_reg_list = raw_reg_list
        self.has_sgl = False
        self.sgl_list = []
    def add_sgl(self, addr_lo, addr_hi, length, ctrl):
        self.has_sgl = True
        self.sgl_list.append([addr_lo, addr_hi, length, ctrl])
        