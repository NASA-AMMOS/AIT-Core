# Copyright 2016 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

import os
import csv

import bliss
import nose


class TestTlmDictWriter(object):
    test_yaml_file = '/tmp/test.yaml'
    test_outpath = '/tmp'

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

        tlmdict = bliss.tlm.TlmDict(self.test_yaml_file)

        writer = bliss.tlm.TlmDictWriter(tlmdict=tlmdict)
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


class TestTlmConfig(object):
    test_yaml_inc1 = '/tmp/test_inc1.yaml'
    test_yaml_inc2 = '/tmp/test_inc2.yaml'
    test_yaml_main = '/tmp/test_main.yaml'
    test_pkl_main = '/tmp/test_main.pkl'

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

        tlmdict = bliss.tlm.TlmDict(self.test_yaml_main)
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

        tlmdict = bliss.tlm.TlmDict(self.test_yaml_main)
        assert len(tlmdict['OCO3_1553_EHS'].fields) == 5
        assert tlmdict['OCO3_1553_EHS'].fields[4].name == 'field_Z'
        assert tlmdict['OCO3_1553_EHS'].fields[4].bytes == 5

        try:
            os.remove(self.test_yaml_main)
            os.remove(self.test_pkl_main)
        except OSError:
            None

if __name__ == '__main__':
    nose.main()
