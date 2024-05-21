SELECTOR_NAME = 'Selector'
DECOMPOSER_NAME = 'Decomposer'
REFINER_NAME = 'Refiner'
FIELD_EXTRACTOR_NAME = 'FieldExtractor'
SYSTEM_NAME = 'System'
MAX_ROUND = 3  # max try times of one agent talk


build_question_template = """
Given the following database schema and some example values, please construct five questions with reference to the following requirements:

- Questions cannot be open-ended. The answer to the question is a specific value or entity or multiple rows of records.
- Answers to questions can be obtained with a single SQL query or multiple SQL queries.
- Please refer to the given database schema and construct the question using the given example values as much as possible, such as including some example values in the question.
- Imitate human questioning methods and give some vague questions appropriately. For example, you can use some abbreviations instead of full names, and use time ranges instead of specific times.
- Please make sure you ask questions in a variety of ways.
- For each question, please extract key fields from the question and convert it into the COMMENTs of the corresponding column names in the database. Please extract all possible key fields and their corresponding COMMENTs.
- Please ask questions in Chinese

/* A example is shown below */
[database schema]
CREATE TABLE student(
    s_id VARCHAR(20) NOT NULL COMMENT '学生编号',
    s_name VARCHAR(20) NOT NULL COMMENT '学生姓名',
    s_birth VARCHAR(20) NOT NULL COMMENT '学生出生日期',
    s_sex VARCHAR(10) NOT NULL COMMENT '学生性别',
    PRIMARY KEY(s_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE course(
    c_id VARCHAR(20) NOT NULL COMMENT '课程编号',
    c_name VARCHAR(20) NOT NULL COMMENT '课程名称',
    t_id VARCHAR(20) NOT NULL COMMENT '教师编号',
    PRIMARY KEY(c_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE teacher(
    t_id VARCHAR(20) NOT NULL COMMENT '教师编号',
    t_name VARCHAR(20) NOT NULL COMMENT '教师姓名',
    PRIMARY KEY(t_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE score(
    s_id VARCHAR(20) NOT NULL COMMENT '学生编号',
    c_id VARCHAR(20) NOT NULL COMMENT '课程编号',
    s_score INT NOT NULL COMMENT '分数',
    PRIMARY KEY(s_id, c_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

[example values]
{{
    'student.s_name': ['张三', '李四', '王五', '赵六', '孙七', '周八'],
    'student.s_birth': ['1990-01-01', '1990-02-02', '1990-03-03', '1990-04-04', '1990-05-05', '1990-06-06'],
    'student.s_sex': ['男', '女', '男', '女', '男', '女'],
    'course.c_name': ['语文', '数学', '英语', '物理', '化学', '生物'],
    'teacher.t_name': ['张老师', '李老师', '王老师', '赵老师', '孙老师', '周老师'],
}}

[questions and key fields]
question: 张三的数学成绩是多少？
thought: 张三-->student.s_name-->学生姓名, 数学-->course.c_name-->课程名称, 成绩-->score.s_score-->分数
key fields: [student.s_name, course.c_name, score.s_score]
COMMENTs: [学生姓名, 课程名称, 分数]

question: 语文课程的平均分是多少？
thought: 语文-->course.c_name-->课程名称, 平均分-->score.s_score-->分数
key fields: [course.c_name, score.s_score]
COMMENTs: [课程名称, 分数]

question: 张老师教的课程有哪些？
thought: 张老师-->teacher.t_name-->教师姓名, 课程-->course.c_name-->课程名称
key fields: [teacher.t_name, course.c_name]
COMMENTs: [教师姓名, 课程名称]

question: 物理课有多少男生的分数大于90分？
thought: 物理-->course.c_name-->课程名称, 男生-->student.s_sex-->学生性别, 90分-->score.s_score-->分数
key fields: [course.c_name, student.s_sex, score.s_score]
COMMENTs: [课程名称, 学生性别, 分数]

question: 有哪些男生的语文成绩大于90分？
thought: 哪些男生-->student.s_name-->学生姓名, 男生-->student.s_sex-->学生性别, 语文-->course.c_name-->课程名称, 90分-->score.s_score-->分数
key fields: [student.s_name, student.s_sez, course.c_name, score.s_score]
COMMENTs: [学生姓名, 学生性别, 课程名称, 分数]

/* Given the database schema and example values below */
[database schema]
{db_schema}
[example values]
{example_values}

/* Construct questions based on the given database schema and example values */
[questions and key fields]
"""


selector_template = """
As an experienced and professional database administrator, your task is to analyze a user question and a database schema to provide relevant information. The database schema consists of table descriptions, each containing multiple column descriptions. Your goal is to identify the relevant tables and columns based on the user question and evidence provided.

[Instruction]:
1. Discard any tables or columns that are not related to the user question and evidence.
2. Sort the columns in each relevant table in descending order of relevance.
3. Ensure that at least 3 tables are included in the final output JSON.
4. The output should be in JSON format.

[Requirements]:
1. If a table has LESS THAN or EQUAL TO 10 columns, mark it as "keep_all".
2. If a table is completely irrelevant to the user question and evidence, mark it as "drop_all".
3. If some columns in a table are relevant to the user question and evidence, mark the table as an array containing the relevant column names.
4. Prioritize the columns in each relevant table based on their relevance.
5. Pelase make sure the selected columns are existing in the corresponding tables.
6. The final output should should contain the oprations to be performed on each table.

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
【Example values】
{{
    'account.account_id': [1, 2, 3, 4, 5],
    'account.district_id': [1, 2, 3, 4, 5],
    'account.frequency': ['monthly', 'monthly', 'monthly', 'monthly', 'monthly'],
    'account.date': [2020-01-01, 2020-01-01, 2020-01-01, 2020-01-01, 2020-01-01],
    'client.client_id': [1, 2, 3, 4, 5],
    'client.gender': ['M', 'F', 'M', 'F', 'M'],
    'client.birth_date': [1990-01-01, 1995-01-01, 1992-01-01, 1998-01-01, 1991-01-01],
    'client.district_id': [1, 2, 3, 4, 5],
    'loan.loan_id': [1, 2, 3, 4, 5],
    'loan.account_id': [1, 2, 3, 4, 5],
    'district.district_id': [1, 2, 3, 4, 5],
}}
【Relevant tables and columns in JSON fromat】
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
【Example values】
{example_values}
【Relevant tables and columns in JSON fromat】
"""


new_decompose_template = """
Given a 【Database schema】 description,【Example values】 and the 【Question】, you need to use valid {db_type} and understand the database and knowledge, and then decompose the question into subquestions for text-to-SQL generation.
When generating SQL, we should always consider constraints:
【Constraints】
- In `SELECT <column>`, just select needed columns in the 【Question】 without any unnecessary column or value
- In `FROM <table>` or `JOIN <table>`, do not include unnecessary table
- If use max or min func, `JOIN <table>` FIRST, THEN use `SELECT MAX(<column>)` or `SELECT MIN(<column>)`
- If [Value examples] of <column> has 'None' or None, use `JOIN <table>` or `WHERE <column> is NOT NULL` is better
- If use `ORDER BY <column> ASC|DESC`, add `GROUP BY <column>` before to select distinct values
- Use `LIMIT` to restrict the number of rows returned when necessary
- IMPORTANT: Pelase make sure the selected columns are existing in the corresponding tables.
- Please use the original Chinese entity names such as person names, location names in the SQL query, rather than translating them into English.
- Please make sure the generated SQL is compatible with the {db_type} database.
- When generating SQL for sub questions, if the subsequent sub questions need to use the SQL generated by the previous sub questions, please use the previously generated SQL in the subquery or JOIN operation, and do not assume any query results.
- If the question is asking for a value or statistic of the value, please return the sum or difference according to the question: SELECT SUM(column_name) FROM table_name
- If the question is asking for a value at a specific year, please use the date column to filter the date to the specific year: WHERE date BETWEEN '2022-01-01' AND '2022-12-31'
- If the question is asking for a comparison between two entities, please make sure to compare or order the corresponding value and return target entity_name: SELECT entity_name FROM table_name WHERE column_name = (SELECT MAX(column_name) FROM table_name)
- If a question asks what a numeric value is, there may be one or more matching rows in the database, return the sum of the values corresponding to those rows: SELECT SUM(column_name) FROM table_name
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

【Example values】
{{
    'frpm.CDSCode': ['01000000000000', '01000000000001', '01000000000002', '01000000000003', '01000000000004'],
    'frpm.Charter School (Y/N)': [0, 1, 0, 1, 0],
    'frpm.Enrollment (Ages 5-17)': [100, 200, 300, 400, 500],
    'frpm.Free Meal Count (Ages 5-17)': [10, 20, 30, 40, 50],
}}

【Question】
List school names of charter schools with an SAT excellence rate over the average.

【Solution】
Decompose the question into sub questions, based on the given 【Database schema】, 【Constraints】, and 【Example values】, and generate the SQL after thinking step by step:
Sub question 1: Get the average value of SAT excellence rate of charter schools.
SQL
```sql
SELECT AVG(CAST(T2.NumGE1500 AS REAL) / T2.NumTstTakr)
    FROM frpm AS T1
    INNER JOIN satscores AS T2
    ON T1.CDSCode = T2.cds
    WHERE T1.Charter School (Y/N) = 1
```

Sub question 2: List out school names of charter schools with an SAT excellence rate over the average.
SQL
```sql
SELECT T2.sname
  FROM frpm AS T1
  INNER JOIN satscores AS T2
  ON T1.CDSCode = T2.cds
  WHERE T2.sname IS NOT NULL
  AND T1.Charter School (Y/N) = 1
  AND CAST(T2.NumGE1500 AS REAL) / T2.NumTstTakr > (
    SELECT AVG(CAST(T4.NumGE1500 AS REAL) / T4.NumTstTakr)
    FROM frpm AS T3
    INNER JOIN satscores AS T4
    ON T3.CDSCode = T4.cds
    WHERE T3.Charter School (Y/N) = 1
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

【Example values】
{{
    'account.account_id': [1, 2, 3, 4, 5],
    'account.district_id': [1, 2, 3, 4, 5],
    'account.frequency': ['monthly', 'monthly', 'monthly', 'monthly', 'monthly'],
    'account.date': [2020-01-01, 2020-01-01, 2020-01-01, 2020-01-01, 2020-01-01],
    'client.client_id': [1, 2, 3, 4, 5],
}}

【Question】
What is the gender of the youngest client who opened account in the lowest average salary branch?

【Solution】
Decompose the question into sub questions, based on the given 【Database schema】, 【Constraints】, and 【Example values】, and generate the SQL after thinking step by step:
Sub question 1: What is the district_id of the branch with the lowest average salary?
SQL
```sql
SELECT district_id
  FROM district
  ORDER BY A11 ASC
  LIMIT 1
```

Sub question 2: What is the youngest client who opened account in the lowest average salary branch?
SQL
```sql
SELECT T1.client_id
  FROM client AS T1
  INNER JOIN district AS T2
  ON T1.district_id = T2.district_id
  ORDER BY T2.A11 ASC, T1.birth_date DESC 
  LIMIT 1
```

Sub question 3: What is the gender of the youngest client who opened account in the lowest average salary branch?
SQL
```sql
SELECT T1.gender
  FROM client AS T1
  INNER JOIN district AS T2
  ON T1.district_id = T2.district_id
  ORDER BY T2.A11 ASC, T1.birth_date DESC 
  LIMIT 1 
```
Question Solved.

==========

【Database schema】
{desc_str}

【Foreign keys】
{fk_str}

【Example values】
{example_values}

【Question】
{query}

【Solution】
Decompose the question into sub questions, based on the given 【Database schema】, 【Constraints】, and 【Example values】, and generate the SQL after thinking step by step:

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
【SQL error】 
{sql_error}
【Exception class】
{exception_class}

Now please fixup old SQL and generate new SQL again.
【correct SQL】
"""


refiner_template_din = """
#### For the given question, use the provided 【Database schema】, 【Foreign keys】, 【Example values】 and 【Execution result】 to fix the given 【{db_type} SQL Query】 for any issues. If there are any problems, fix them. If there are no issues, return the 【{db_type} SQL Query】 as is.
#### Use the following instructions for fixing the SQL QUERY:
1) Use the database values that are explicitly mentioned in the question.
2) Pay attention to the columns that are used for the JOIN by using the Foreign_keys.
3) Use DESC and DISTINCT when needed.
4) Pay attention to the columns that are used for the GROUP BY statement.
5) Pay attention to the columns that are used for the SELECT statement.
6) Only change the GROUP BY clause when necessary (Avoid redundant columns in GROUP BY).
7) Use GROUP BY on one column only.
8) Use LIMIT to restrict the number of rows returned when necessary
10) Return the fixed SQL query only (WITHOUT ANY EXPLANATION).
11) IMPORTANT: Please refer to the 【Execution result】, if there are any error in the 【Execution result】, please fix the SQL QUERY.
12) IMPORTANT: If selected columns in the {db_type} SQL QUERY are not existed in the corresponding tables, please replace the column names with the correct column names in the FIXED SQL QUERY.
13) Please use the original Chinese entity names such as person names, location names in the SQL query, rather than translating them into English.
14) If the question is asking for a value at a specific year, please use the date column to filter the date to the specific year: WHERE date BETWEEN '2022-01-01' AND '2022-12-31'
15) If the question is asking for a comparison between two entities, please make sure to compare or order the corresponding value and return target entity_name: SELECT entity_name FROM table_name WHERE column_name = (SELECT MAX(column_name) FROM table_name)
16) IMPORTANT: If a question asks what a numeric value is, there may be one or more matching rows in the database, return the sum of the values corresponding to those rows: SELECT SUM(column_name) FROM table_name
17) IMPORTANT: If there are multiple rows in the 【Execution result】, please fix the 【{db_type} SQL Query】 to  return the sum of the values corresponding to those rows: SELECT SUM(column_name) FROM table_name

【Database schema】
{desc_str}
【Foreign keys】
{fk_str}
【Example values】
{example_values}
【Question】
{query}
【{db_type} SQL Query】
{sql}
【Execution result】
{execution_result}

## Attention:
1) If the given SQL query is None, generate the correct SQL query and return it (WITHOUT ANY EXPLANATION).
2) If the given SQL query is correct, return it as is (WITHOUT ANY EXPLANATION!!!).
3) If selected columns in the {db_type} SQL QUERY are not existed in the corresponding tables, please replace the column names with the correct column names in the FIXED SQL QUERY.
4) Return the fixed SQL query only (WITHOUT ANY EXPLANATION).
5) Please follow the SQL format to return the fixed SQL query.
8) IMPORTANT: Pelase make sure the selected columns are existing in the corresponding tables.
9) Please use the original Chinese entity names such as person names, location names in the SQL query, rather than translating them into English.
10) If the question is asking for a value or statistic of the value, please return the sum or difference according to the question: SELECT SUM(column_name) FROM table_name
11) If the question is asking for a value at a specific year, please use the date column to filter the date to the specific year: WHERE date BETWEEN '2022-01-01' AND '2022-12-31'
12) If the question is asking for a comparison between two entities, please make sure to compare or order the corresponding value and return target entity_name: SELECT entity_name FROM table_name WHERE column_name = (SELECT MAX(column_name) FROM table_name)
13) IMPORTANT: If a question asks what a numeric value is, there may be one or more matching rows in the database, return the sum of the values corresponding to those rows: SELECT SUM(column_name) FROM table_name
14) IMPORTANT: If there are multiple rows in the 【Execution result】, please fix the 【{db_type} SQL Query】 to return the sum of the values corresponding to those rows: SELECT SUM(column_name) FROM table_name

【Fixed SQL Query】
"""
