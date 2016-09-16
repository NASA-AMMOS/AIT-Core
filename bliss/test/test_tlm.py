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

if __name__ == '__main__':
    nose.main()
