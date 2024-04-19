import re

def extract_foreign_keys(sql_commands):
    foreign_keys = {}
    for sql_command in sql_commands:
        table_name_match = re.search(r'CREATE TABLE (\w+)', sql_command)
        if table_name_match:
            table_name = table_name_match.group(1)
            foreign_key_matches = re.findall(r'FOREIGN KEY\("(.*?)"\) REFERENCES (\w+) \("(.*?)"\)', sql_command)
            if foreign_key_matches:
                foreign_keys[table_name] = [f"{table_name}.{fk[0]}={fk[1]}.{fk[2]}" for fk in foreign_key_matches]
    return foreign_keys

if __name__ == "__main__":
    sql_commands = [
        '''CREATE TABLE concert (
                "concert_ID" INTEGER,
                "concert_Name" TEXT,
                "Theme" TEXT,
                "Stadium_ID" TEXT,
                "Year" TEXT,
                PRIMARY KEY ("concert_ID"),
                FOREIGN KEY("Stadium_ID") REFERENCES stadium ("Stadium_ID")
        )''',
        '''CREATE TABLE singer (
                "Singer_ID" INTEGER,
                "Name" TEXT,
                "Country" TEXT,
                "Song_Name" TEXT,
                "Song_release_year" TEXT,
                "Age" INTEGER,
                "Is_male" BOOLEAN,
                PRIMARY KEY ("Singer_ID")
        )''',
        '''CREATE TABLE singer_in_concert (
                "concert_ID" INTEGER,
                "Singer_ID" TEXT,
                PRIMARY KEY ("concert_ID", "Singer_ID"),
                FOREIGN KEY("concert_ID") REFERENCES concert ("concert_ID"),
                FOREIGN KEY("Singer_ID") REFERENCES singer ("Singer_ID")
        )''',
        '''CREATE TABLE stadium (
                "Stadium_ID" INTEGER,
                "Location" TEXT,
                "Name" TEXT,
                "Capacity" INTEGER,
                "Highest" INTEGER,
                "Lowest" INTEGER,
                "Average" INTEGER,
                PRIMARY KEY ("Stadium_ID")
        )'''
    ]

    foreign_keys = extract_foreign_keys(sql_commands)
    print(foreign_keys)
    foreign_keys_str = str()
    for table, fks in foreign_keys.items():
            foreign_keys_str += f"{table}: {fks}\n"
    print(foreign_keys_str)
