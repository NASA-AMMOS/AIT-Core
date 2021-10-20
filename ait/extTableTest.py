import ait.core.table as table

# tab_dict = table.FSWTabDict("/Users/jehofman/AIT-Core/config/table.yaml")
# tab_dict.load(filename=tab_dict.filename)

table_dict = table.getDefaultFSWTabDict()
table_dict.create('MyTable')
table_dict.load(filename=table_dict.filename)
