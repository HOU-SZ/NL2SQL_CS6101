import re

def apply_dictionary(sql_commands, foreign_keys, dictionary):
    modified_sql_commands = []
    modified_foreign_keys = {}

    for sql_command in sql_commands:
        table_name_match = re.search(r'CREATE TABLE (\w+)', sql_command)
        if table_name_match:
            table_name = table_name_match.group(1)
            if table_name in dictionary:
                if dictionary[table_name] == "keep_all":
                    modified_sql_commands.append(sql_command)
                    if table_name in foreign_keys:
                        modified_foreign_keys[table_name] = foreign_keys[table_name]
                elif dictionary[table_name] == "drop_all":
                    # Drop the table and its foreign keys
                    if table_name in foreign_keys:
                        del foreign_keys[table_name]
                    continue
                elif isinstance(dictionary[table_name], list):
                    # Keep only specified columns
                    columns_to_keep = set(dictionary[table_name])
                    lines = sql_command.split("\n")
                    new_lines = [lines[0]]  # Keep the CREATE TABLE line
                    for line in lines[1:]:
                        column_name_match = re.search(r'"(\w+)"', line)
                        if column_name_match and column_name_match.group(1) in columns_to_keep:
                            new_lines.append(line)
                    new_lines.append(")")
                    modified_sql_commands.append("\n".join(new_lines))
                    if table_name in foreign_keys:
                        modified_foreign_keys[table_name] = foreign_keys[table_name]
            else:
                modified_sql_commands.append(sql_command)

    return modified_sql_commands, modified_foreign_keys

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

    foreign_keys = {
        "concert": ["concert.Stadium_ID=stadium.Stadium_ID"],
        "singer_in_concert": [
            "singer_in_concert.concert_ID=concert.concert_ID",
            "singer_in_concert.Singer_ID=singer.Singer_ID"
        ]
    }

    dictionary = {
        "concert": "keep_all",
        "singer": ["Singer_ID", "Name", "Country", "Song_Name", "Song_release_year", "Age"],
        "singer_in_concert": "keep_all",
        "stadium": "drop_all"
    }

    modified_sql_commands, modified_foreign_keys = apply_dictionary(sql_commands, foreign_keys, dictionary)

    print("SQL create table命令：")
    for sql_command in modified_sql_commands:
        print(sql_command)

    print("\nforeign keys信息：")
    for table_name, fks in modified_foreign_keys.items():
        for fk in fks:
            print(fk)
