import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect(
    r'..\database\concert_singer\concert_singer.sqlite')
cursor = conn.cursor()

# Execute a sample query
query = """
    SELECT   COUNT(*)
    FROM   singer
"""
cursor.execute(query)

# Fetch and print the results
results = cursor.fetchall()
for row in results:
    print(row)

# Close cursor and connection
cursor.close()
conn.close()
