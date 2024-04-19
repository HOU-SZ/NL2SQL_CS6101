import json
def parse_data(data_str):
    lines = data_str.strip().split('\n')
    header = lines[0].split()
    data = []
    for line in lines[1:]:
        values = line.split('\t')
        data.append(values)
    return data

data_str = '''Stadium_ID\tLocation\tName\tCapacity\tHighest\tLowest\tAverage\n1\tRaith Rovers\tStark\'s Park\t10104\t4812\t1294\t2106\n2\tAyr United\tSomerset Park\t11998\t2363\t1057\t1477\n3\tEast Fife\tBayview Stadium\t2000\t1980\t533\t864\n'''

data = parse_data(data_str)

schema = {
    "table_name": "stadium",
    "columns": ["Stadium_ID", "Location", "Name", "Capacity", "Highest", "Lowest", "Average"]
}

def generate_insert_sql(table_name, columns, data):
    insert_sql_list = []
    for row in data:
        # temp = []
        # for value in row:
        #     if isinstance(value, str):
        #         temp.append(f'"{value}"')
        #     else:
        #         temp.append(str(value))
        # print(temp)
        print(row)
        for i in range(len(row)):
            converted = json.loads(row[i])
            print(type(converted))
        values = ', '.join(f'"{value}"' if isinstance(json.loads(value), str) else value for value in row)
        print(values)
        insert_sql = f'INSERT INTO "{table_name}" VALUES ({values});'
        insert_sql_list.append(insert_sql)
    return insert_sql_list

insert_sql_list = generate_insert_sql(schema["table_name"], schema["columns"], data)

for insert_sql in insert_sql_list:
    print(insert_sql)
