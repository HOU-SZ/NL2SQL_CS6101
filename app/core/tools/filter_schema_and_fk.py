import re


def apply_dictionary(sql_commands, foreign_keys, dictionary):
    modified_sql_commands = {}
    droped_tables = []
    droped_table_columns = {}
    # print("sql_commands:", sql_commands)

    for sql_command in sql_commands:
        table_name_match = ""
        if 'CREATE TABLE "' in sql_command:
            table_name_match = re.search(
                r'CREATE TABLE "(.*?)"', sql_command)
        else:
            table_name_match = re.search(
                r'CREATE TABLE (.*?)\s*\(', sql_command)
        if table_name_match:
            table_name = table_name_match.group(1)
            if table_name in dictionary:
                if dictionary[table_name] == "keep_all":
                    modified_sql_commands[table_name] = sql_command
                elif dictionary[table_name] == "drop_all":
                    # Drop the table and its foreign keys
                    if table_name in foreign_keys:
                        del foreign_keys[table_name]
                    droped_tables.append(table_name)
                elif isinstance(dictionary[table_name], list):
                    # Keep only specified columns
                    columns_to_keep = set(dictionary[table_name])
                    lines = sql_command.split("\n")
                    new_lines = [lines[0]]  # Keep the CREATE TABLE line
                    for line in lines[1:]:
                        column_name_match = re.search(r'"(\w+)"', line)
                        if column_name_match and column_name_match.group(1) in columns_to_keep:
                            new_lines.append(line)
                        elif column_name_match and column_name_match.group(1) not in columns_to_keep:
                            if table_name not in droped_table_columns:
                                droped_table_columns[table_name] = []
                            droped_table_columns[table_name].append(
                                column_name_match.group(1))
                    new_lines.append(");")
                    modified_sql_commands[table_name] = "\n".join(
                        new_lines)
            else:
                modified_sql_commands[table_name] = sql_command

    # Remove foreign keys constraints referencing dropped tables (right of the "=" sign)
    for table in droped_tables:
        for table_name, fks in foreign_keys.items():
            for fk in fks:
                right_table = fk.split("=")[1].split(".")[0]
                if right_table == table:
                    fks.remove(fk)
            # remove the command line form the corresponding create table command
            for table_name, sql_command in modified_sql_commands.items():
                if table_name == table:
                    del modified_sql_commands[table_name]
                elif "REFERENCES " + table in sql_command:
                    modified_sql_commands[table_name] = re.sub(
                        r'FOREIGN KEY\("(.*?)"\) REFERENCES ' + table + ' \("(.*?)"\)', '', sql_command)
                    modified_sql_commands[table_name] = re.sub(
                        r'\n\s*\n', '\n', modified_sql_commands[table_name])
                    modified_sql_commands[table_name] = re.sub(
                        r',\s*,', ',', modified_sql_commands[table_name])

    # Remove foreign keys constraints referencing columns that are not kept (left of the "=" sign)
    for table_name, fks in foreign_keys.items():
        for fk in fks:
            left_table = fk.split("=")[0].split(".")[0]
            left_column = fk.split("=")[0].split(".")[1]
            if left_table in dictionary and type(dictionary[left_table]) == list and left_column not in dictionary[left_table]:
                fks.remove(fk)

    # Remove foreign keys constraints referencing columns that are not kept (right of the "=" sign)
    for table_name, fks in foreign_keys.items():
        for fk in fks:
            right_table = fk.split("=")[1].split(".")[0]
            right_column = fk.split("=")[1].split(".")[1]
            if right_table in dictionary and type(dictionary[right_table]) == list and right_column not in dictionary[right_table]:
                fks.remove(fk)

    # Remove all unnecessary REFERENCES in the modified_sql_commands
    for table_name, droped_columns in droped_table_columns.items():
        for column in droped_columns:
            for table_name, sql_command in modified_sql_commands.items():
                match_str_1 = "REFERENCES " + \
                    table_name + '("' + column + '")'
                match_str_2 = "REFERENCES " + \
                    table_name + ' ("' + column + '")'
                if match_str_1 in sql_command:
                    sql_command = sql_command.replace(match_str_1, '')
                elif match_str_2 in sql_command:
                    sql_command = sql_command.replace(match_str_2, '')
                modified_sql_commands[table_name] = sql_command
                modified_sql_commands[table_name] = re.sub(
                    r'\n\s*\n', '\n', modified_sql_commands[table_name])
                modified_sql_commands[table_name] = re.sub(
                    r',\s*,', ',', modified_sql_commands[table_name])
    return modified_sql_commands.values(), foreign_keys


if __name__ == "__main__":
    sql_commands = [
        '''CREATE TABLE "concert" (
                "concert_ID" INTEGER,
                "concert_Name" TEXT,
                "Theme" TEXT,
                "Stadium_ID" TEXT,
                "Year" TEXT,
                PRIMARY KEY ("concert_ID"),
                FOREIGN KEY("Stadium_ID") REFERENCES stadium ("Stadium_ID")
        );''',
        '''CREATE TABLE "singer" (
                "Singer_ID" INTEGER,
                "Name" TEXT,
                "Country" TEXT,
                "Song_Name" TEXT,
                "Song_release_year" TEXT,
                "Age" INTEGER,
                "Is_male" BOOLEAN,
                PRIMARY KEY ("Singer_ID")
        );''',
        '''CREATE TABLE "singer_in_concert" (
                "concert_ID" INTEGER,
                "Singer_ID" TEXT,
                PRIMARY KEY ("concert_ID", "Singer_ID"),
                FOREIGN KEY("concert_ID") REFERENCES concert ("concert_ID"),
                FOREIGN KEY("Singer_ID") REFERENCES singer ("Singer_ID")
        );''',
        '''CREATE TABLE "stadium" (
                "Stadium_ID" INTEGER,
                "Location" TEXT,
                "Name" TEXT,
                "Capacity" INTEGER,
                "Highest" INTEGER,
                "Lowest" INTEGER,
                "Average" INTEGER,
                PRIMARY KEY ("Stadium_ID")
        );'''
    ]

    foreign_keys = {
        "concert": ["concert.Stadium_ID=stadium.Stadium_ID"],
        "singer_in_concert": [
            "singer_in_concert.concert_ID=concert.concert_ID",
            "singer_in_concert.Singer_ID=singer.Singer_ID"
        ]
    }

    dictionary = {
        "concert": "drop_all",
        "singer": "keep_all",
        "singer_in_concert": "drop_all",
        "stadium": "drop_all"
    }

    modified_sql_commands, foreign_keys = apply_dictionary(
        sql_commands, foreign_keys, dictionary)

    print("SQL create table命令：")
    for sql_command in modified_sql_commands:
        print(sql_command)

    print("\nforeign keys信息：")
    print(foreign_keys)
