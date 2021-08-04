import os.path
import tempfile
import unittest

from ait.core import table

test_table = """
- !FSWTable
  name: test_type
  delimiter: ","
  header:
    - !FSWColumn
      name: MAGIC_NUM
      desc: The first column in our header
      format: "%x"
      units: none
      type:  U8
      bytes: 0

    - !FSWColumn
      name: UPTYPE
      desc: The second column in our header
      format: "%u"
      units: none
      type:  U8
      bytes: 1

    - !FSWColumn
      name: VERSION
      desc: The third column in our header
      format: "%u"
      units: none
      type:  U8
      bytes: 2

  columns:
    - !FSWColumn
      name: COLUMN_ONE
      desc: First FSW Table Column
      format: "%u"
      units: none
      type:  MSB_U16
      bytes: [0,1]

    - !FSWColumn
      name: COLUMN_TWO
      desc: Second FSW Table Column
      format: "%u"
      units: none
      type:  MSB_U16
      bytes: [2,3]

    - !FSWColumn
      name: COLUMN_THREE
      desc: Third FSW Table Column
      format: "%u"
      units: none
      type:  U8
      bytes: 4
      enum:
        0: TEST_ENUM_0
        1: TEST_ENUM_1
        2: TEST_ENUM_2
        3: TEST_ENUM_3
"""


class TestTableEncode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table_defn_path = os.path.join(tempfile.gettempdir(), "test_table.yaml")

        with open(cls.table_defn_path, "w") as infile:
            infile.write(test_table)

        cls.tabdict = table.FSWTabDict(cls.table_defn_path)

    def test_enum_encode(self):
        defn = self.tabdict["test_type"]

        table_data = ["13,12,11", "1,2,TEST_ENUM_3", "4,5,TEST_ENUM_0"]

        encoded = defn.encode(text_in=table_data)
        assert len(encoded) == 13

        # Check header
        assert encoded[0] == 13
        assert encoded[1] == 12
        assert encoded[2] == 11

        # Check first row
        assert encoded[3] == 0
        assert encoded[4] == 1
        assert encoded[5] == 0
        assert encoded[6] == 2
        assert encoded[7] == 3

        # Check second row
        assert encoded[8] == 0
        assert encoded[9] == 4
        assert encoded[10] == 0
        assert encoded[11] == 5
        assert encoded[12] == 0

    def test_encode_text_no_hdr(self):
        defn = self.tabdict["test_type"]

        table_data = ["13,12,11", "1,2,3", "4,5,6"]

        encoded = defn.encode(text_in=table_data)
        assert len(encoded) == 13

        # Check header
        assert encoded[0] == 13
        assert encoded[1] == 12
        assert encoded[2] == 11

        # Check first row
        assert encoded[3] == 0
        assert encoded[4] == 1
        assert encoded[5] == 0
        assert encoded[6] == 2
        assert encoded[7] == 3

        # Check second row
        assert encoded[8] == 0
        assert encoded[9] == 4
        assert encoded[10] == 0
        assert encoded[11] == 5
        assert encoded[12] == 6

    def test_encode_text_with_hdr(self):
        defn = self.tabdict["test_type"]

        table_data = ["1,2,3", "4,5,6"]

        hdr_vals = [13, 12, 11]

        encoded = defn.encode(text_in=table_data, hdr_vals=hdr_vals)

        assert len(encoded) == 13

        # Check header
        assert encoded[0] == 13
        assert encoded[1] == 12
        assert encoded[2] == 11

        # Check first row
        assert encoded[3] == 0
        assert encoded[4] == 1
        assert encoded[5] == 0
        assert encoded[6] == 2
        assert encoded[7] == 3

        # Check second row
        assert encoded[8] == 0
        assert encoded[9] == 4
        assert encoded[10] == 0
        assert encoded[11] == 5
        assert encoded[12] == 6

    def test_encode_file_no_hdr(self):
        defn = self.tabdict["test_type"]

        table_data = """
        13,12,11
        1,2,3
        4,5,6
        """

        tmp_table_input = os.path.join(tempfile.gettempdir(), "test_table.txt")
        with open(tmp_table_input, "w") as in_file:
            in_file.write(table_data)

        with open(tmp_table_input, "r") as in_file:
            encoded = defn.encode(file_in=in_file)

        assert len(encoded) == 13

        # Check header
        assert encoded[0] == 13
        assert encoded[1] == 12
        assert encoded[2] == 11

        # Check first row
        assert encoded[3] == 0
        assert encoded[4] == 1
        assert encoded[5] == 0
        assert encoded[6] == 2
        assert encoded[7] == 3

        # Check second row
        assert encoded[8] == 0
        assert encoded[9] == 4
        assert encoded[10] == 0
        assert encoded[11] == 5
        assert encoded[12] == 6

        os.remove(tmp_table_input)

    def test_encode_file_with_hdr(self):
        defn = self.tabdict["test_type"]

        table_data = """
        1,2,3
        4,5,6
        """

        hdr_vals = [13, 12, 11]

        tmp_table_input = os.path.join(tempfile.gettempdir(), "test_table.txt")
        with open(tmp_table_input, "w") as in_file:
            in_file.write(table_data)

        with open(tmp_table_input, "r") as in_file:
            encoded = defn.encode(file_in=in_file, hdr_vals=hdr_vals)

        assert len(encoded) == 13

        # Check header
        assert encoded[0] == 13
        assert encoded[1] == 12
        assert encoded[2] == 11

        # Check first row
        assert encoded[3] == 0
        assert encoded[4] == 1
        assert encoded[5] == 0
        assert encoded[6] == 2
        assert encoded[7] == 3

        # Check second row
        assert encoded[8] == 0
        assert encoded[9] == 4
        assert encoded[10] == 0
        assert encoded[11] == 5
        assert encoded[12] == 6

        os.remove(tmp_table_input)


class TestTableDecode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table_defn_path = os.path.join(tempfile.gettempdir(), "test_table.yaml")

        with open(cls.table_defn_path, "w") as infile:
            infile.write(test_table)

        cls.tabdict = table.FSWTabDict(cls.table_defn_path)

    def test_decode_binary(self):
        defn = self.tabdict["test_type"]

        table_data = ["13,12,11", "1,2,8", "4,5,6"]

        encoded = defn.encode(text_in=table_data)

        decoded = defn.decode(bin_in=encoded)

        # Check header
        assert decoded[0][0] == 13
        assert decoded[0][1] == 12
        assert decoded[0][2] == 11

        # Check first row
        assert decoded[1][0] == 1
        assert decoded[1][1] == 2
        assert decoded[1][2] == 8

        # Check first row
        assert decoded[2][0] == 4
        assert decoded[2][1] == 5
        assert decoded[2][2] == 6

    def test_enum_decode(self):
        defn = self.tabdict["test_type"]

        table_data = ["13,12,11", "1,2,TEST_ENUM_3", "4,5,TEST_ENUM_0"]
        encoded = defn.encode(text_in=table_data)

        bin_file = os.path.join(tempfile.gettempdir(), "test_table_in.bin")
        with open(bin_file, "wb") as out_file:
            out_file.write(encoded)

        with open(bin_file, "rb") as out_file:
            decoded = defn.decode(file_in=out_file)

        # Check header
        assert decoded[0][0] == 13
        assert decoded[0][1] == 12
        assert decoded[0][2] == 11

        # Check first row
        assert decoded[1][0] == 1
        assert decoded[1][1] == 2
        assert decoded[1][2] == "TEST_ENUM_3"

        # Check first row
        assert decoded[2][0] == 4
        assert decoded[2][1] == 5
        assert decoded[2][2] == "TEST_ENUM_0"

    def test_enum_decode_raw_values(self):
        defn = self.tabdict["test_type"]

        table_data = ["13,12,11", "1,2,TEST_ENUM_3", "4,5,TEST_ENUM_0"]
        encoded = defn.encode(text_in=table_data)

        bin_file = os.path.join(tempfile.gettempdir(), "test_table_in.bin")
        with open(bin_file, "wb") as out_file:
            out_file.write(encoded)

        with open(bin_file, "rb") as out_file:
            decoded = defn.decode(file_in=out_file, raw=True)

        # Check header
        assert decoded[0][0] == 13
        assert decoded[0][1] == 12
        assert decoded[0][2] == 11

        # Check first row
        assert decoded[1][0] == 1
        assert decoded[1][1] == 2
        assert decoded[1][2] == 3

        # Check first row
        assert decoded[2][0] == 4
        assert decoded[2][1] == 5
        assert decoded[2][2] == 0


class TestBadEnumHandling(unittest.TestCase):
    def test_table_duplicate_enum_load(self):
        test_table = """
        - !FSWTable
          name: test_type
          delimiter: ","
          header:
            - !FSWColumn
              name: MAGIC_NUM
              desc: The first column in our header
              format: "%x"
              units: none
              type:  U8
              bytes: 0

          columns:
            - !FSWColumn
              name: COLUMN_THREE
              desc: Third FSW Table Column
              format: "%u"
              units: none
              type:  U8
              bytes: 4
              enum:
                0: TEST_ENUM_0
                1: TEST_ENUM_1
                2: TEST_ENUM_2
                3: TEST_ENUM_3
                4: TEST_ENUM_0
        """
        table_defn_path = os.path.join(tempfile.gettempdir(), "test_table_dupe_enum.yaml")

        with open(table_defn_path, "w") as infile:
            infile.write(test_table)

        with self.assertLogs('ait', level="ERROR") as cm:
            tabdict = table.FSWTabDict(table_defn_path)
            assert len(cm.output) == 1
