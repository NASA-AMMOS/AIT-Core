#!/usr/bin/env python2.7

# Copyright 2016 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.


import os
import csv
import struct

import nose

from bliss.core import tlm


class TestTlmDictWriter(object):
    test_yaml_file = '/tmp/test.yaml'
    test_outpath   = '/tmp'

    def test_writeToCSV(self):
        yaml_doc = """
        - !Packet
          name: Packet1
          fields:
            - !Field
              name:       col1
              desc:       test column 1
              bytes:      0
              type:       MSB_U16
              mask:       0x10
              enum:
                a: testa
            - !Field
              name: SampleTime
              type: TIME64
              bytes: 1
        """

        csv_row1 = ['col1', '0', '2', '0x10', 'MSB', 'MSB_U16', 'test column 1', 'a: testa']

        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml_doc)

        tlmdict = tlm.TlmDict(self.test_yaml_file)

        writer = tlm.TlmDictWriter(tlmdict=tlmdict)
        writer.writeToCSV(self.test_outpath)

        expected_csv = os.path.join(self.test_outpath, 'Packet1.csv')
        assert os.path.isfile(expected_csv)

        with open(expected_csv, 'rb') as csvfile:
            reader = csv.reader(csvfile)
            # skip header
            reader.next()
            actual_row = reader.next()
            assert actual_row[0] == csv_row1[0]
            assert actual_row[1] == csv_row1[1]
            assert actual_row[4] == csv_row1[4]

        os.remove(self.test_yaml_file)
        os.remove(expected_csv)


class TestFieldDefinition(object):
    test_yaml_test1 = '/tmp/test_test1.yaml'

    yaml_docs_test1 = (
        '- !Packet\n'
        '  name: OCO3_1553_EHS\n'
        '  fields:\n'
        '    - !Field\n'
        '      name: field_1\n'
        '      title: Field 1\n'
        '      type: MSB_U16\n'
    )

    def setUp(self):
        with open(self.test_yaml_test1, 'wb') as out:
            out.write(self.yaml_docs_test1)

    def tearDown(self):
        os.remove(self.test_yaml_test1)

    def test_field_definition(self):
        tlmdict = tlm.TlmDict(self.test_yaml_test1)
        assert tlmdict['OCO3_1553_EHS'].fields[0].name == 'field_1'
        assert tlmdict['OCO3_1553_EHS'].fields[0].title == 'Field 1'

    def test_fld_defn_notitle(self):
        test_yaml_test2 = '/tmp/test_test2.yaml'
        yaml_docs_test2 = (
            '- !Packet\n'
            '  name: OCO3_1553_EHS\n'
            '  fields:\n'
            '    - !Field\n'
            '      name: field_1\n'
            '      type: MSB_U16\n'
        )

        with open(test_yaml_test2, 'wb') as out:
            out.write(yaml_docs_test2)

        tlmdict = tlm.TlmDict(test_yaml_test2)

        assert tlmdict['OCO3_1553_EHS'].fields[0].title == 'field_1'

        os.remove(test_yaml_test2)


class TestTlmConfig(object):
    test_yaml_inc1 = '/tmp/test_inc1.yaml'
    test_yaml_inc2 = '/tmp/test_inc2.yaml'
    test_yaml_main = '/tmp/test_main.yaml'
    test_pkl_main  = '/tmp/test_main.pkl'

    yaml_docs_inc1 = (
        '- !Field\n'
        '  name:  field_A\n'
        '  type:  U8\n'
        '- !Field\n'
        '  name:  field_B\n'
        '  type:  U8\n'
    )
    yaml_docs_inc2 = (
        '- !Field\n'
        '  name:  field_Y\n'
        '  type:  U8\n'
        '- !Field\n'
        '  name:  field_Z\n'
        '  type:  U8\n'
    )

    def setUp(self):
        with open(self.test_yaml_inc1, 'wb') as out:
            out.write(self.yaml_docs_inc1)

        with open(self.test_yaml_inc2, 'wb') as out:
            out.write(self.yaml_docs_inc2)

    def tearDown(self):
        os.remove(self.test_yaml_inc1)
        os.remove(self.test_yaml_inc2)

    def test_yaml_fld_includes(self):
        yaml_docs_main = (
            '- !Packet\n'
            '  name: OCO3_1553_EHS\n'
            '  fields:\n'
            '    - !include /tmp/test_inc1.yaml\n'
            '    - !Field\n'
            '      name: field_1\n'
            '      type: MSB_U16\n'
        )

        with open(self.test_yaml_main, 'wb') as out:
            out.write(yaml_docs_main)

        tlmdict = tlm.TlmDict(self.test_yaml_main)
        assert len(tlmdict['OCO3_1553_EHS'].fields) == 3
        assert tlmdict['OCO3_1553_EHS'].fields[1].name == 'field_B'
        assert tlmdict['OCO3_1553_EHS'].fields[1].bytes == 1

        try:
            os.remove(self.test_yaml_main)
            os.remove(self.test_pkl_main)
        except OSError:
            None

    def test_yaml_fld_includesx2(self):
        yaml_docs_main = (
            '- !Packet\n'
            '  name: OCO3_1553_EHS\n'
            '  fields:\n'
            '    - !include /tmp/test_inc1.yaml\n'
            '    - !Field\n'
            '      name: field_1\n'
            '      type: MSB_U16\n'
            '    - !include /tmp/test_inc2.yaml\n'
        )

        with open(self.test_yaml_main, 'wb') as out:
            out.write(yaml_docs_main)

        tlmdict = tlm.TlmDict(self.test_yaml_main)
        assert len(tlmdict['OCO3_1553_EHS'].fields) == 5
        assert tlmdict['OCO3_1553_EHS'].fields[4].name == 'field_Z'
        assert tlmdict['OCO3_1553_EHS'].fields[4].bytes == 5

        try:
            os.remove(self.test_yaml_main)
            os.remove(self.test_pkl_main)
        except OSError:
            None

    def test_yaml_fld_includes_nested(self):
        test_yaml_inc3 = '/tmp/test_inc3.yaml'
        yaml_docs_inc3 = (
            '- !include /tmp/test_inc1.yaml\n'
            '- !include /tmp/test_inc2.yaml\n'
        )

        with open(test_yaml_inc3, 'wb') as out:
            out.write(yaml_docs_inc3)

        yaml_docs_main = (
            '- !Packet\n'
            '  name: OCO3_1553_EHS\n'
            '  fields:\n'
            '    - !Field\n'
            '      name: field_1\n'
            '      type: MSB_U16\n'
            '    - !include /tmp/test_inc3.yaml\n'
        )

        with open(self.test_yaml_main, 'wb') as out:
            out.write(yaml_docs_main)

        tlmdict = tlm.TlmDict(self.test_yaml_main)
        assert len(tlmdict['OCO3_1553_EHS'].fields) == 5
        assert tlmdict['OCO3_1553_EHS'].fields[4].name == 'field_Z'
        assert tlmdict['OCO3_1553_EHS'].fields[4].bytes == 5

        try:
            os.remove(test_yaml_inc3)
            os.remove(self.test_yaml_main)
            os.remove(self.test_pkl_main)
        except OSError:
            None

    def test_yaml_fld_includes_nestedx2(self):
        test_yaml_inc3 = '/tmp/test_inc3.yaml'
        yaml_docs_inc3 = (
            '- !include /tmp/test_inc1.yaml\n'
            '- !include /tmp/test_inc2.yaml\n'
        )

        with open(test_yaml_inc3, 'wb') as out:
            out.write(yaml_docs_inc3)

        test_yaml_inc4 = '/tmp/test_inc4.yaml'
        yaml_docs_inc4 = (
            '    - !include /tmp/test_inc3.yaml\n'
            '    - !Field\n'
            '      name: field_FOO\n'
            '      type: MSB_U16\n'
        )

        with open(test_yaml_inc4, 'wb') as out:
            out.write(yaml_docs_inc4)

        yaml_docs_main = (
            '- !Packet\n'
            '  name: OCO3_1553_EHS\n'
            '  fields:\n'
            '    - !Field\n'
            '      name: field_1\n'
            '      type: MSB_U16\n'
            '    - !include /tmp/test_inc4.yaml\n'
        )

        with open(self.test_yaml_main, 'wb') as out:
            out.write(yaml_docs_main)

        tlmdict = tlm.TlmDict(self.test_yaml_main)
        assert len(tlmdict['OCO3_1553_EHS'].fields) == 6
        assert tlmdict['OCO3_1553_EHS'].fields[5].name == 'field_FOO'
        assert tlmdict['OCO3_1553_EHS'].fields[5].bytes == [6, 7]

        try:
            os.remove(test_yaml_inc3)
            os.remove(test_yaml_inc4)
            os.remove(self.test_yaml_main)
            os.remove(self.test_pkl_main)
        except OSError:
            None

    def test_yaml_pkt_includes(self):
        yaml_docs_inc3 = (
            '- !Packet\n'
            '  name: OCO3_TEST1\n'
            '  fields:\n'
            '    - !include /tmp/test_inc1.yaml\n'
        )

        test_yaml_inc3 = '/tmp/test_inc3.yaml'
        with open(test_yaml_inc3, 'wb') as out:
            out.write(yaml_docs_inc3)

        yaml_docs_inc4 = (
            '- !Packet\n'
            '  name: OCO3_TEST_2\n'
            '  fields:\n'
            '    - !include /tmp/test_inc2.yaml\n'
        )

        test_yaml_inc4 = '/tmp/test_inc4.yaml'
        with open(test_yaml_inc4, 'wb') as out:
            out.write(yaml_docs_inc4)

        yaml_docs_main = (
            '- !Packet\n'
            '  name: OCO3_1553_EHS\n'
            '  fields:\n'
            '    - !include /tmp/test_inc1.yaml\n'
            '    - !Field\n'
            '      name: field_1\n'
            '      type: MSB_U16\n'
            '    - !include /tmp/test_inc2.yaml\n'
            '- !include /tmp/test_inc3.yaml\n'
            '- !include /tmp/test_inc4.yaml\n'
        )

        with open(self.test_yaml_main, 'wb') as out:
            out.write(yaml_docs_main)

        tlmdict = tlm.TlmDict(self.test_yaml_main)
        assert len(tlmdict['OCO3_1553_EHS'].fields) == 5
        assert tlmdict['OCO3_1553_EHS'].fields[4].name == 'field_Z'
        assert tlmdict['OCO3_1553_EHS'].fields[4].bytes == 5

        assert len(tlmdict['OCO3_TEST1'].fields) == 2
        assert tlmdict['OCO3_TEST1'].fields[1].name == 'field_B'
        assert tlmdict['OCO3_TEST1'].fields[1].bytes == 1

        try:
            os.remove(test_yaml_inc3)
            os.remove(test_yaml_inc4)
            os.remove(self.test_yaml_main)
            os.remove(self.test_pkl_main)
        except OSError:
            None



def testArray ():
    """
    # This test will use the following TLM dictionary definitions:

    - !Packet
      name: P
      fields:
        - !Field
          name: A
          type: MSB_U16[3]

    """
    defn   = tlm.TlmDict(testArray.__doc__)['P']
    packet = tlm.Packet(defn, struct.pack('>HHH', 1, 2, 3))

    assert packet.A == [1, 2, 3]


if __name__ == '__main__':
    nose.main()
