SELECTOR_NAME = 'Selector'
DECOMPOSER_NAME = 'Decomposer'
REFINER_NAME = 'Refiner'
SYSTEM_NAME = 'System'
MAX_ROUND = 3  # max try times of one agent talk

selector_template = """
As an experienced and professional database administrator, your task is to analyze a user question and a database schema to provide relevant information. The database schema consists of table descriptions, each containing multiple column descriptions. Your goal is to identify the relevant tables and columns based on the user question and evidence provided.

[Instruction]:
1. Discard any table schema that is not related to the user question and evidence.
2. Sort the columns in each relevant table in descending order of relevance and keep the top 6 columns.
3. Ensure that at least 3 tables are included in the final output JSON.
4. The output should be in JSON format.

Requirements:
1. If a table has less than or equal to 10 columns, mark it as "keep_all".
2. If a table is completely irrelevant to the user question and evidence, mark it as "drop_all".
3. Prioritize the columns in each relevant table based on their relevance.

Here is a typical example:

==========
【DB_ID】 banking_system
【Schema】
CREATE TABLE account (
    account_id INT PRIMARY KEY, COMMENT the id of the account
    district_id INT, COMMENT location of branch
    frequency VARCHAR(50), COMMENT frequency of the acount
    date DATE COMMENT the creation date of the account
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

CREATE TABLE client (
    client_id INT PRIMARY KEY, COMMENT the unique number
    gender CHAR(1), COMMENT gender. F: female . M: male
    birth_date DATE, COMMENT birth date
    district_id INT COMMENT location of branch
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

CREATE TABLE loan (
    loan_id INT PRIMARY KEY, COMMENT the id number identifying the loan data
    account_id INT, COMMENT the id number identifying the account
    date DATE, COMMENT the date when the loan is approved
    amount INT, COMMENT the amount of the loan
    duration INT, COMMENT the duration the loan
    payments INT, COMMENT the payments the loan
    status CHAR(1) COMMENT the status of the loan
    FOREIGN KEY (account_id) REFERENCES account(account_id)
);

CREATE TABLE district (
    district_id INT PRIMARY KEY, COMMENT location of branch
    A2 FLOAT, COMMENT area in square kilometers
    A4 INT, COMMENT number of inhabitants
    A5 INT, COMMENT number of households
    A6 FLOAT, COMMENT literacy rate
    A7 INT, COMMENT number of entrepreneurs
    A8 INT, COMMENT number of cities
    A9 INT, COMMENT number of schools
    A10 INT, COMMENT number of hospitals
    A11 INT, COMMENT average salary
    A12 FLOAT, COMMENT poverty rate
    A13 FLOAT, COMMENT unemployment rate
    A15 INT COMMENT number of crimes
);
【Foreign keys】
client: ['client.district_id = district.district_id']
account: ['account.district_id = district.district_id']
loan: ['loan.account_id = account.account_id']
【Question】
What is the gender of the youngest client who opened account in the lowest average salary branch?
【Evidence】
Later birthdate refers to younger age; A11 refers to average salary
【Answer】
```json
{{
  "account": "keep_all",
  "client": "keep_all",
  "loan": "drop_all",
  "district": ["district_id", "A11", "A2", "A4", "A6", "A7"]
}}
```
Question Solved.

==========

Here is a new example, please start answering:

【DB_ID】 {db_id}
【Schema】
{desc_str}
【Foreign keys】
{fk_str}
【Question】
{query}
【Evidence】
{evidence}
【Answer】
"""

decompose_template_spider = """
Given a 【Database schema】 description, and the 【Question】, you need to use valid SQLite and understand the database, and then generate the corresponding SQL.

==========

【Database schema】
CREATE TABLE "stadium" (
    "Stadium_ID" int,
    "Location" text,
    "Name" text,
    "Capacity" int,
    "Highest" int,
    "Lowest" int,
    "Average" int,
    PRIMARY KEY ("Stadium_ID")
);

CREATE TABLE "concert" (
    "concert_ID" int,
    "concert_Name" text,
    "Theme" text,
    "Stadium_ID" text,
    "Year" text,
    PRIMARY KEY ("concert_ID"),
    FOREIGN KEY ("Stadium_ID") REFERENCES "stadium"("Stadium_ID")
);
【Foreign keys】
concert: ['concert.Stadium_ID=stadium.Stadium_ID']
【Question】
Show the stadium name and the number of concerts in each stadium.

SQL
```sql
SELECT T1.Name, COUNT(*) FROM stadium AS T1 JOIN concert AS T2 ON T1.Stadium_ID = T2.Stadium_ID GROUP BY T1.Stadium_ID
```

Question Solved.

==========

【Database schema】
CREATE TABLE "singer" (
    "Singer_ID" int,
    "Name" text,
    "Country" text,
    "Song_Name" text,
    "Song_release_year" text,
    "Age" int,
    PRIMARY KEY ("Singer_ID")
);

CREATE TABLE "concert" (
    "concert_ID" int,
    "concert_Name" text,
    "Theme" text,
    "Stadium_ID" text,
    "Year" text,
    PRIMARY KEY ("concert_ID"),
);
CREATE TABLE "singer_in_concert" (
    "concert_ID" int,
    "Singer_ID" text,
    PRIMARY KEY ("concert_ID","Singer_ID"),
    FOREIGN KEY ("concert_ID") REFERENCES "concert"("concert_ID"),
    FOREIGN KEY ("Singer_ID") REFERENCES "singer"("Singer_ID")
);
【Foreign keys】
singer_in_concert: ['singer_in_concert.concert_ID=concert.concert_ID', 'singer_in_concert.Singer_ID=singer.Singer_ID']
【Question】
Show the name and the release year of the song by the youngest singer.


SQL
```sql
SELECT Song_Name, Song_release_year FROM singer WHERE Age = (SELECT MIN(Age) FROM singer)
```

Question Solved.

==========

【Database schema】
{desc_str}
【Foreign keys】
{fk_str}
【Question】
{query}

SQL

"""

decompose_template_bird = """
Given a 【Database schema】 description, a knowledge 【Evidence】 and the 【Question】, you need to use valid SQLite and understand the database and knowledge, and then decompose the question into subquestions for text-to-SQL generation.
When generating SQL, we should always consider constraints:
【Constraints】
- In `SELECT <column>`, just select needed columns in the 【Question】 without any unnecessary column or value
- In `FROM <table>` or `JOIN <table>`, do not include unnecessary table
- If use max or min func, `JOIN <table>` FIRST, THEN use `SELECT MAX(<column>)` or `SELECT MIN(<column>)`
- If [Value examples] of <column> has 'None' or None, use `JOIN <table>` or `WHERE <column> is NOT NULL` is better
- If use `ORDER BY <column> ASC|DESC`, add `GROUP BY <column>` before to select distinct values

==========

【Database schema】
CREATE TABLE frpm (
    CDSCode VARCHAR(50) PRIMARY KEY, COMMENT CDSCode
    Charter School (Y/N), COMMENT 0: N;. 1: Y
    Enrollment (Ages 5-17) FLOAT, COMMENT Enrollment (Ages 5-17)
    Free Meal Count (Ages 5-17) FLOAT COMMENT Free Meal Count (Ages 5-17)
    FOREIGN KEY (CDSCode) REFERENCES satscores(cds)
);

CREATE TABLE satscores (
    cds VARCHAR(50) PRIMARY KEY, COMMENT California Department Schools
    sname VARCHAR(50), COMMENT school name
    NumTstTakr INT, COMMENT number of test takers in each school
    AvgScrMath INT, COMMENT average scores in Math
    NumGE1500 INT COMMENT Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500
);
【Foreign keys】
frpm: ['frpm.CDSCode=satscores.cds']
【Question】
List school names of charter schools with an SAT excellence rate over the average.
【Evidence】
Charter schools refers to `Charter School (Y/N)` = 1 in the table frpm; Excellence rate = NumGE1500 / NumTstTakr


Decompose the question into sub questions, considering 【Constraints】, and generate the SQL after thinking step by step:
Sub question 1: Get the average value of SAT excellence rate of charter schools.
SQL
```sql
SELECT AVG(CAST(T2.`NumGE1500` AS REAL) / T2.`NumTstTakr`)
    FROM frpm AS T1
    INNER JOIN satscores AS T2
    ON T1.`CDSCode` = T2.`cds`
    WHERE T1.`Charter School (Y/N)` = 1
```

Sub question 2: List out school names of charter schools with an SAT excellence rate over the average.
SQL
```sql
SELECT T2.`sname`
  FROM frpm AS T1
  INNER JOIN satscores AS T2
  ON T1.`CDSCode` = T2.`cds`
  WHERE T2.`sname` IS NOT NULL
  AND T1.`Charter School (Y/N)` = 1
  AND CAST(T2.`NumGE1500` AS REAL) / T2.`NumTstTakr` > (
    SELECT AVG(CAST(T4.`NumGE1500` AS REAL) / T4.`NumTstTakr`)
    FROM frpm AS T3
    INNER JOIN satscores AS T4
    ON T3.`CDSCode` = T4.`cds`
    WHERE T3.`Charter School (Y/N)` = 1
  )
```

Question Solved.

==========

【Database schema】
CREATE TABLE account (
    account_id INT PRIMARY KEY, COMMENT the id of the account
    district_id INT, COMMENT location of branch
    frequency VARCHAR(50), COMMENT frequency of the acount
    date DATE COMMENT the creation date of the account
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

CREATE TABLE client (
    client_id INT PRIMARY KEY, COMMENT the unique number
    gender CHAR(1), COMMENT gender. F: female . M: male
    birth_date DATE, COMMENT birth date
    district_id INT COMMENT location of branch
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

CREATE TABLE district (
    district_id INT PRIMARY KEY, COMMENT location of branch
    A4 INT, COMMENT number of inhabitants
    A11 INT, COMMENT average salary
);
【Foreign keys】
client: ['client.district_id = district.district_id']
account: ['account.district_id = district.district_id']
【Question】
What is the gender of the youngest client who opened account in the lowest average salary branch?
【Evidence】
Later birthdate refers to younger age; A11 refers to average salary

Decompose the question into sub questions, considering 【Constraints】, and generate the SQL after thinking step by step:
Sub question 1: What is the district_id of the branch with the lowest average salary?
SQL
```sql
SELECT `district_id`
  FROM district
  ORDER BY `A11` ASC
  LIMIT 1
```

Sub question 2: What is the youngest client who opened account in the lowest average salary branch?
SQL
```sql
SELECT T1.`client_id`
  FROM client AS T1
  INNER JOIN district AS T2
  ON T1.`district_id` = T2.`district_id`
  ORDER BY T2.`A11` ASC, T1.`birth_date` DESC 
  LIMIT 1
```

Sub question 3: What is the gender of the youngest client who opened account in the lowest average salary branch?
SQL
```sql
SELECT T1.`gender`
  FROM client AS T1
  INNER JOIN district AS T2
  ON T1.`district_id` = T2.`district_id`
  ORDER BY T2.`A11` ASC, T1.`birth_date` DESC 
  LIMIT 1 
```
Question Solved.

==========

【Database schema】
{desc_str}
【Foreign keys】
{fk_str}
【Question】
{query}
【Evidence】
{evidence}

Decompose the question into sub questions, considering 【Constraints】, and generate the SQL after thinking step by step:
"""


refiner_template = """
【Instruction】
When executing SQL below, some errors occurred, please fix up SQL based on query and database info.
Solve the task step by step if you need to. Using SQL format in the code block, and indicate script type in the code block.
When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
【Constraints】
- In `SELECT <column>`, just select needed columns in the 【Question】 without any unnecessary column or value
- In `FROM <table>` or `JOIN <table>`, do not include unnecessary table
- If use max or min func, `JOIN <table>` FIRST, THEN use `SELECT MAX(<column>)` or `SELECT MIN(<column>)`
- If [Value examples] of <column> has 'None' or None, use `JOIN <table>` or `WHERE <column> is NOT NULL` is better
- If use `ORDER BY <column> ASC|DESC`, add `GROUP BY <column>` before to select distinct values
【Query】
COMMENT {query}
【Evidence】
{evidence}
【Database info】
{desc_str}
【Foreign keys】
{fk_str}
【old SQL】
```sql
{sql}
```
【SQLite error】 
{sqlite_error}
【Exception class】
{exception_class}

Now please fixup old SQL and generate new SQL again.
【correct SQL】
"""


refiner_template_din = """
#### For the given question, use the provided database schema, and foreign keys to fix the given SQLite SQL QUERY for any issues. If there are any problems, fix them. If there are no issues, return the SQLite SQL QUERY as is.
#### Use the following instructions for fixing the SQL QUERY:
1) Use the database values that are explicitly mentioned in the question.
2) Pay attention to the columns that are used for the JOIN by using the Foreign_keys.
3) Use DESC and DISTINCT when needed.
4) Pay attention to the columns that are used for the GROUP BY statement.
5) Pay attention to the columns that are used for the SELECT statement.
6) Only change the GROUP BY clause when necessary (Avoid redundant columns in GROUP BY).
7) Use GROUP BY on one column only.

【Database schema】
{desc_str}
【Foreign keys】
{fk_str}
【Question】
{query}
【SQLite SQL Query】
{sql}

【Fixed SQL Query】
"""
