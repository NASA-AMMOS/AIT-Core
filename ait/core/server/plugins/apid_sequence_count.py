'''
Implements a plugin which maintains a sequence count for each APID
'''
import os
import pickle
import ait
import ait.core
from ait.core.server.plugins import Plugin
from ait.core import log


class APIDSequenceCounter(Plugin):
    '''
    Checks the sequence count field of CCSDS packets to ensure that packets aren't dropped.
    Maintains a dictionary of the expected sequence count value for each APID.
    The dictionary is saved and loaded as .pkl files so that the count persists across sessions.

    example setup in config.yaml:

    - plugin:
        name: ait.core.server.plugins.apid_sequence_path.APIDSequenceCounter
        inputs:
            - AOS_to_CCSDS
        seq_count_dict:
            path: tlm_seq_count_dict.pkl

    '''
    def __init__(self, inputs=None, outputs=None, zmq_args=None, seq_count_dict=None):

        super().__init__(inputs, outputs, zmq_args)

        self.pickle_path = None
        if seq_count_dict:
            if 'path' in seq_count_dict:
                self.pickle_path = seq_count_dict['path']
                self.count_dictionary = self.load_pickle_dict(self.pickle_path)
        if self.pickle_path == None:
            log.error("no path specified for pickled dictionary")
            self.pickle_path = '/'.join(ait.config.get('cmddict')['filename'].split('/')[:-1]) + "/tlm_seq_count.pkl"
            log.info(f"creating pickle file at {self.pickle_path}")
            self.count_dictionary = {}

    def process(self, input_data):
        '''
        checks sequence counts of incoming CCSDS packets

        :param input_data: CCSDS packet
        :type input_data: bytearray, bytes
        '''
        packet_apid = self.get_packet_apid(input_data)
        packet_sequence_count = self.get_packet_sequence_count(input_data)
        self.check_sequence_count(packet_apid, packet_sequence_count)
        
        self.publish(input_data)

    def load_pickle_dict(self, pickle_path):
        '''
        loads a pickled dictionary from the specified path

        :param pickle_path: path of pickled dictionary
        :type pickle_path: string, path
        :returns: unpickled dictionary
        :rtype: dict
        '''
        if os.path.exists(pickle_path):
            with open(pickle_path, 'rb') as handle:
                unpickled_dict = pickle.load(handle)
            return unpickled_dict
        else:
            log.info(f"unable to find pkl object at {pickle_path}, creating empty dictionary")
            empty_dict = {}
            return empty_dict

    def save_pickle_dict(self, dictionary, pickle_path):
        '''
        saves a dictionary as a pickle object at specified path

        :param dictionary: dictionary to be pickled
        :type dictionary: dict
        :param pickle_path: path of pickled dictionary
        :type pickle_path: string, path
        '''
        with open(pickle_path, 'wb') as handle:
            pickle.dump(dictionary, handle, protocol=pickle.HIGHEST_PROTOCOL)
        log.info(f"Saved pickle file at {pickle_path}")

    def get_packet_apid(self, packet):
        '''
        Returns the APID (as integer) for a given packet (bytearray)
        Assumes that the APID is the last 11 bits of the first two bytes

        :param packet: CCSDS packet as bytes
        :type packet: bytes, bytearray
        :returns: packet APID
        :rtype: int
        '''
        packet_apid_bits = bytearray(b1 & b2 for b1, b2 in zip(packet[0:2], bytearray(b'\x07\xff')))
        apid = int.from_bytes(packet_apid_bits, byteorder='big')
        return apid

    def get_packet_sequence_count(self, packet):
        '''
        Returns the sequence count (as integer) for a given packet (bytearray)
        Assumes that the sequence count is the last 14 bits of bytes 3-4

        :param packet: CCSDS packet as bytes
        :type packet: bytes, bytearray
        :returns: packet sequence count
        :rtype: int
        '''
        seq_count_bits = bytearray(b1 & b2 for b1, b2 in zip(packet[2:4], bytearray(b'\x3f\xff')))
        seq_count = int.from_bytes(seq_count_bits, byteorder='big')
        return seq_count

    def check_sequence_count(self, apid, sequence_count):
        '''
        Checks the actual sequence count against the expected sequence count and raises an error in the event of a discrepancy.
        Updates the class variable with the new expected count value

        :param apid: CCSDS packet APID as integer
        :type apid: int
        :param sequence_count: CCSDS packet sequence count as integer
        :type sequence_count: int
        '''
        keys = self.count_dictionary.keys()

        # check actual count against expected count
        if apid in keys:
            expected_count = self.count_dictionary[apid]
            if sequence_count != expected_count:
                log.info(f'PACKET SEQUENCE COUNT ERROR FOR APID {apid}. Expected {expected_count} but received {sequence_count}')
        else: #case where new apid is received. Count should start at 0.
            if sequence_count != 0:
                log.info(f'PACKET SEQUENCE COUNT ERROR FOR APID {apid}. Expected 0 but received {sequence_count}')

        # update count dictionary
        if sequence_count == 16383: #sequence count wraps at 16383 (due to 14 bit field)
            self.count_dictionary[apid] = 0
        else:
            self.count_dictionary[apid] = sequence_count + 1

    def __del__(self):
        self.save_pickle_dict(self.count_dictionary, self.pickle_path)
