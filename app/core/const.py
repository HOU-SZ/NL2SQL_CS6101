SELECTOR_NAME = 'Selector'
DECOMPOSER_NAME = 'Decomposer'
REFINER_NAME = 'Refiner'
FIELD_EXTRACTOR_NAME = 'FieldExtractor'
SYSTEM_NAME = 'System'
MAX_ROUND = 3  # max try times of one agent talk

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
【Evidence】
Later birthdate refers to younger age; A11 refers to average salary
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
【Evidence】
{evidence}
【Relevant tables and columns in JSON fromat】
"""

decompose_template_spider = """
Given a 【Database schema】 description, and the 【Question】, you need to use valid {db_type} and understand the database, and then generate the corresponding SQL.

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
Given a 【Database schema】 description, a knowledge 【Evidence】 and the 【Question】, you need to use valid {db_type} and understand the database and knowledge, and then decompose the question into subquestions for text-to-SQL generation.
When generating SQL, we should always consider constraints:
【Constraints】
- In `SELECT <column>`, just select needed columns in the 【Question】 without any unnecessary column or value
- In `FROM <table>` or `JOIN <table>`, do not include unnecessary table
- If use max or min func, `JOIN <table>` FIRST, THEN use `SELECT MAX(<column>)` or `SELECT MIN(<column>)`
- If [Value examples] of <column> has 'None' or None, use `JOIN <table>` or `WHERE <column> is NOT NULL` is better
- If use `ORDER BY <column> ASC|DESC`, add `GROUP BY <column>` before to select distinct values
- Use `LIMIT` to restrict the number of rows returned when necessary
- Use `AS` to give an alias to the table name or column name or subquery
- Pelase make sure the selected columns are existing in the corresponding tables.
- Please use the original Chinese company_name and company_province in the SQL query, rather than translating them into English.
- Please make sure the generated SQL is compatible with the {db_type} database.
- When generating SQL for sub questions, if the subsequent sub questions need to use the SQL generated by the previous sub questions, please use the previously generated SQL in the subquery or JOIN operation, and do not assume any query results.
- Please only select the necessary tables and columns in the SQL query. For example, if the question is "哪家公司最早成立", you only need to select the company_name column. If the question is "比亚迪是在什么时候在主板上市的", you need to select the list_date column.
- If the question is asking for a value or statistic of the value, please return the sum or difference according to the question. For example, if the question is "2022年晨光文具的筹资活动现金流出小计是多少？", you need to return the sum of the corresponding column: SELECT SUM(sub_total_of_cos_from_fa) FROM cash_flow_CN_STOCK_A"
- If the question is asking for a value at a specific year, please use the date column to filter the data. For example, if the question is "2022年晨光文具的现金流量表中的经营活动现金流量净额是多少？", you need to add the date filter in the WHERE clause: WHERE report_date BETWEEN '2022-01-01' AND '2022-12-31'
- A example: If the question is "2022年建设银行的筹资活动现金流入小计是多少？", you need to return the sum value of the corresponding column at 2022: SELECT SUM(sub_total_of_ci_from_fa) FROM cash_flow_CN_STOCK_A JOIN basic_info_CN_STOCK_A ON cash_flow_CN_STOCK_A.instrument = basic_info_CN_STOCK_A.instrument WHERE date BETWEEN '2022-01-01' AND '2022-12-31' AND basic_info_CN_STOCK_A.company_name = '建设银行股份有限公司';
- If the question is asking for a comparison between two companies, please make sure to compare or order the corresponding value and return target company_name. For example, if the question is "2022年建设银行和晨光文具哪家公司的支付其他与经营活动有关的现金更多？", you need to return the company_name: SELECT T2.company_name FROM cash_flow_CN_STOCK_A AS T1 INNER JOIN basic_info_CN_STOCK_A AS T2 ON T1.instrument = T2.instrument WHERE (T2.company_name = '建设银行股份有限公司' OR T2.company_name = '上海晨光文具股份有限公司') AND YEAR(T1.report_date) = 2022 ORDER BY T1.other_cash_paid_related_to_oa DESC LIMIT 1;
- If a question asks what a numeric value is, there may be one or more matching rows in the database, return the sum of the values corresponding to those rows. If you don't know how many rows will match, you can return the sum of all the values. For example, if the question is "2022年东方证券的偿还债务支付的现金是多少？", you need to return the sum value of the corresponding column at 2022: SELECT SUM(cash_pay_for_debt) FROM cash_flow_CN_STOCK_A AS T1 INNER JOIN basic_info_CN_STOCK_A AS T2 ON T1.instrument = T2.instrument WHERE YEAR(T1.report_date) = 2022 AND T2.company_name = '东方证券股份有限公司';

==========

【Database schema】
CREATE TABLE balance_sheet_CN_STOCK_A (
	date DATE NOT NULL COMMENT '公告日', 
	instrument VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '股票代码', 
	report_date DATE NOT NULL COMMENT '报告期', 
	PRIMARY KEY (date, instrument, report_date)
)ENGINE=InnoDB COMMENT='资产负债表' COLLATE utf8mb4_unicode_ci DEFAULT CHARSET=utf8mb4

CREATE TABLE basic_info_CN_STOCK_A (
	instrument VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL COMMENT '证券代码', 
	company_name VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci COMMENT '公司名称', 
	PRIMARY KEY (instrument)
)ENGINE=InnoDB COMMENT='A股股票基本信息' DEFAULT CHARSET=utf8mb3

CREATE TABLE cash_flow_CN_STOCK_A (
	instrument VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '股票代码', 
	report_date DATE COMMENT '报告期', 
	si_final_balance_of_cce DOUBLE COMMENT '现金等价物的期末余额', 
)ENGINE=InnoDB COMMENT='现金流量表' COLLATE utf8mb4_unicode_ci DEFAULT CHARSET=utf8mb4

CREATE TABLE income_CN_STOCK_A (
	instrument VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '股票代码', 
	report_date DATE COMMENT '报告期', 
)ENGINE=InnoDB COMMENT='利润表' COLLATE utf8mb4_unicode_ci DEFAULT CHARSET=utf8mb4

【Foreign keys】
balance_sheet_CN_STOCK_A: ['balance_sheet_CN_STOCK_A.instrument = basic_info_CN_STOCK_A.instrument']
cash_flow_CN_STOCK_A: ['cash_flow_CN_STOCK_A.instrument = basic_info_CN_STOCK_A.instrument']
income_CN_STOCK_A: ['income_CN_STOCK_A.instrument = basic_info_CN_STOCK_A.instrument']

【Question】
2022年工商银行的现金等价物的期末余额是多少？

【Evidence】
None


Decompose the question into sub questions, based on the given 【Database schema】, considering 【Constraints】, and generate the SQL after thinking step by step:
Sub question 1: 找到工商银行在表basic_info_CN_STOCK_A中的instrument代码。
SQL
```sql
SELECT instrument 
FROM basic_info_CN_STOCK_A
WHERE company_name = '中国工商银行股份有限公司'
```

Sub question 2: 找到2022年工商银行在表cash_flow_CN_STOSTOCK_A中的所有si_final_balance_of_cce的总和。
SQL
```sql
SELECT SUM(si_final_balance_of_cce )
FROM cash_flow_CN_STOCK_A
WHERE instrument = (
    SELECT instrument 
    FROM basic_info_CN_STOCK_A
    WHERE company_name = '中国工商银行股份有限公司'
)
AND report_date BETWEEN '2022-01-01' AND '2022-12-31'
```

Question Solved.

==========

【Database schema】
CREATE TABLE balance_sheet_CN_STOCK_A (
	date DATE NOT NULL COMMENT '公告日', 
	instrument VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '股票代码', 
	report_date DATE NOT NULL COMMENT '报告期', 
	PRIMARY KEY (date, instrument, report_date)
)ENGINE=InnoDB COMMENT='资产负债表' COLLATE utf8mb4_unicode_ci DEFAULT CHARSET=utf8mb4

CREATE TABLE basic_info_CN_STOCK_A (
	instrument VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL COMMENT '证券代码', 
	company_name VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci COMMENT '公司名称', 
	PRIMARY KEY (instrument)
)ENGINE=InnoDB COMMENT='A股股票基本信息' DEFAULT CHARSET=utf8mb3

CREATE TABLE cash_flow_CN_STOCK_A (
	instrument VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '股票代码', 
	other_cash_paid_related_to_oa DOUBLE COMMENT '支付其他与经营活动有关的现金', 
)ENGINE=InnoDB COMMENT='现金流量表' COLLATE utf8mb4_unicode_ci DEFAULT CHARSET=utf8mb4

CREATE TABLE income_CN_STOCK_A (
	instrument VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '股票代码', 
)ENGINE=InnoDB COMMENT='利润表' COLLATE utf8mb4_unicode_ci DEFAULT CHARSET=utf8mb4

【Foreign keys】
balance_sheet_CN_STOCK_A: ['balance_sheet_CN_STOCK_A.instrument = basic_info_CN_STOCK_A.instrument']
cash_flow_CN_STOCK_A: ['cash_flow_CN_STOCK_A.instrument = basic_info_CN_STOCK_A.instrument']
income_CN_STOCK_A: ['income_CN_STOCK_A.instrument = basic_info_CN_STOCK_A.instrument']

【Question】
2022年海通证券和浪潮软件哪家公司的支付其他与经营活动有关的现金更高？

【Evidence】
None

Decompose the question into sub questions, based on the given 【Database schema】, considering 【Constraints】, and generate the SQL after thinking step by step:
Sub question 1: 获取2022年海通证券的支付其他与经营活动有关的现金总和。
SQL
```sql
SELECT SUM(other_cash_paid_related_to_oa)
FROM cash_flow_CN_STOCK_A AS T1
  INNER JOIN basic_info_CN_STOCK_A AS T2
  ON T1.instrument = T2.instrument
  WHERE T2.company_name = '海通证券股份有限公司'
  AND YEAR(report_date) = 2022
```

Sub question 2: 获取2022年浪潮软件的支付其他与经营活动有关的现金总和。
SQL
```sql
SELECT SUM(other_cash_paid_related_to_oa)
FROM cash_flow_CN_STOCK_A AS T1
    INNER JOIN basic_info_CN_STOCK_A AS T2
    ON T1.instrument = T2.instrument
    WHERE T2.company_name = '浪潮软件股份有限公司'
    AND YEAR(report_date) = 2022
```

Sub question 3: 比较2022年海通证券和浪潮软件哪家公司的支付其他与经营活动有关的现金更高。
SQL
```sql
SELECT T2.company_name
FROM cash_flow_CN_STOCK_A AS T1
    INNER JOIN basic_info_CN_STOCK_A AS T2
    ON T1.instrument = T2.instrument
    WHERE (T2.company_name = '海通证券股份有限公司' OR T2.company_name = '浪潮软件股份有限公司')
    AND YEAR(report_date) = 2022
    ORDER BY SUM(other_cash_paid_related_to_oa) DESC
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

Decompose the question into sub questions, based on the given 【Database schema】, considering 【Constraints】, and generate the SQL after thinking step by step:
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
#### For the given question, use the provided database schema, and foreign keys to fix the given {db_type} SQL QUERY for any issues. If there are any problems, fix them. If there are no issues, return the {db_type} SQL QUERY as is.
#### Use the following instructions for fixing the SQL QUERY:
1) Use the database values that are explicitly mentioned in the question.
2) Pay attention to the columns that are used for the JOIN by using the Foreign_keys.
3) Use DESC and DISTINCT when needed.
4) Pay attention to the columns that are used for the GROUP BY statement.
5) Pay attention to the columns that are used for the SELECT statement.
6) Only change the GROUP BY clause when necessary (Avoid redundant columns in GROUP BY).
7) Use GROUP BY on one column only.
8) Use LIMIT to restrict the number of rows returned when necessary
9) If the given SQL query is None, return correct SQL query.
10) Return the fixed SQL query only (WITHOUT ANY EXPLANATION).
11) If selected columns in the {db_type} SQL QUERY are not existed in the corresponding tables, please replace the column names with the correct column names in the FIXED SQL QUERY.
12) When generating SQL for sub questions, if the subsequent sub questions need to use the SQL generated by the previous sub questions, please use the previously generated SQL in the subquery or JOIN operation, and do not assume any query results.
13) Please only select the necessary tables and columns in the SQL query.
14) If the question is asking for a value or statistic of the value, please return the sum or difference according to the question: SELECT SUM(column_name) FROM table_name
15) If the question is asking for a value at a specific year, please use the date column to filter the date to the specific year: WHERE date BETWEEN '2022-01-01' AND '2022-12-31'
16) If the question is asking for a comparison between two companies, please make sure to compare or order the corresponding value and return target company_name: SELECT company_name FROM table_name WHERE column_name = (SELECT MAX(column_name) FROM table_name)
17) If a question asks what a numeric value is, there may be one or more matching rows in the database, return the sum of the values corresponding to those rows. If you don't know how many rows will match, you can return the sum of all the values: SELECT SUM(column_name) FROM table_name

【Database schema】
{desc_str}
【Foreign keys】
{fk_str}
【Question】
{query}
【{db_type} SQL Query】
{sql}

## Attention:
1) If the given SQL query is None, generate the correct SQL query and return it (WITHOUT ANY EXPLANATION).
2) If the given SQL query is correct, return it as is (WITHOUT ANY EXPLANATION!!!).
3) If selected columns in the {db_type} SQL QUERY are not existed in the corresponding tables, please replace the column names with the correct column names in the FIXED SQL QUERY.
4) Return the fixed SQL query only (WITHOUT ANY EXPLANATION).
5) Please follow the SQL format to return the fixed SQL query.
6) Please make sure the generated SQL is compatible with the {db_type} database.
7) When generating SQL for sub questions, if the subsequent sub questions need to use the SQL generated by the previous sub questions, please use the previously generated SQL in the subquery or JOIN operation, and do not assume any query results.
8) Please only select the necessary tables and columns in the SQL query.
9) If the question is asking for a value or statistic of the value, please return the sum or difference according to the question: SELECT SUM(column_name) FROM table_name
10) If the question is asking for a value at a specific year, please use the date column to filter the date to the specific year: WHERE date BETWEEN '2022-01-01' AND '2022-12-31'
11) If the question is asking for a comparison between two companies, please make sure to compare or order the corresponding value and return target company_name: SELECT company_name FROM table_name WHERE column_name = (SELECT MAX(column_name) FROM table_name)
12) If a question asks what a numeric value is, there may be one or more matching rows in the database, return the sum of the values corresponding to those rows. If you don't know how many rows will match, you can return the sum of all the values: SELECT SUM(column_name) FROM table_name

【Fixed SQL Query】
"""

field_extractor_template = """
Extract the main target field name from the given questions.

/* Some example questions and extracted target fields */
Question: 2022年建设银行的现金等价物的期末余额是多少？
Target fields: [现金等价物的期末余额, 证券名称, 报告日期]

Question: 比较广东的晨光文具和比亚迪，哪家公司在2022年的手续费及佣金收入更高？
Target fields: [手续费及佣金收入, 公司名称, 公司省份, 报告日期]

Question: 请计算2022年上港集团的固定资产及在建工程占总资产的比例
Target fields: [固定资产, 在建工程, 总资产, 公司名称, 报告日期]

Question: 请列出2022年应付手续费及佣金占总负债比例最高的五家公司？
Target fields: [应付手续费及佣金, 总负债, 公司名称, 报告日期]

Question: 同享科技2023年归属于母公司所有者的净利润年增长率是多少？
Target fields: [归属于母公司所有者的净利润, 公司名称, 报告日期]

Question: 2023第一季度上港集团的营业总收入环比增长率是多少？
Target fields: [营业总收入, 公司名称, 报告日期]

Question: 请问在广东省成立的公司在总公司数量中占比多少？
Target fields: [公司省份]

Question: 查询上市公司所在地为上海的公司数量？
Target fields: [公司省份]

Question: 查看2023在科创板上市的公司数量的同比增长？
Target fields: [上市板块]

Question: 请找出上市日期最早的五家公司的股票代码，公司名称和上市日期。
Target fields: [股票代码, 公司名称, 上市日期]

Question: 请找出所有已退市的公司的股票代码和退市日期。
Target fields: [股票代码, 退市日期]

Question: 请找出所有在北京成立的公司的股票代码和公司名称。
Target fields: [公司名称, 公司省份, 股票代码]

Question: 过去五年中，哪家公司的预收款项与应付账款比率最高？
Target fields: [预收款项, 应付账款, 公司名称, 报告日期]

/* Please extract the target fields from the following question */
Question: {question}
Target fields:
"""

new_field_extractor_template = """
Given the following problem, you need to extract as many key fields as possible from the problem. The extracted key fields will be used to match database tables and columns. The more key fields you extract, the more accurate the resulting SQL statement will be. Please return the key fields as a list. Note that only the key fields are returned, not the specific values.

/* Examples of some questions and key fields */
Question: 计算每个季度的新能源汽车销售总量
Key fields: ["日期", "销售量", "新能源汽车"]

Question: 23年成员企业营收排名
Key fields: ["日期", "营收", "成员企业"]

Question: 请问8月份服务范围和服务态度分别有多少张工单？
Key fields: ["日期", "服务范围", "服务态度", "工单"]

Question: 有哪几个行业的企业可以经营餐饮服务类工作？
Key fields: ["行业名称", "企业", "餐饮服务"]

Question: 2020年Q1北京新能源销量渗透率
Key fields: ["日期", "销量", "新能源", "渗透率"]

/* Please extract the key fields from the following question */
Question: {question}
Key fields: 
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
- Pelase make sure the selected columns are existing in the corresponding tables.
- Please use the original Chinese company_name and company_province in the SQL query, rather than translating them into English.
- Please make sure the generated SQL is compatible with the {db_type} database.
- When generating SQL for sub questions, if the subsequent sub questions need to use the SQL generated by the previous sub questions, please use the previously generated SQL in the subquery or JOIN operation, and do not assume any query results.
- Please only select the necessary tables and columns in the SQL query.
- If the question is asking for a value or statistic of the value, please return the sum or difference according to the question: SELECT SUM(column_name) FROM table_name
- If the question is asking for a value at a specific year, please use the date column to filter the date to the specific year: WHERE date BETWEEN '2022-01-01' AND '2022-12-31'
- If the question is asking for a comparison between two companies, please make sure to compare or order the corresponding value and return target company_name: SELECT company_name FROM table_name WHERE column_name = (SELECT MAX(column_name) FROM table_name)
- If a question asks what a numeric value is, there may be one or more matching rows in the database, return the sum of the values corresponding to those rows. If you don't know how many rows will match, you can return the sum of all the values: SELECT SUM(column_name) FROM table_name
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

# desc_str = """
# CREATE TABLE balance_sheet_CN_STOCK_A (
# 	instrument VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '股票代码',
# 	report_date DATE NOT NULL COMMENT '报告期',
# 	charge_and_commi_payable DOUBLE COMMENT '应付手续费及佣金',
# 	contract_liab DOUBLE COMMENT '合同负债',
# 	estimated_liab DOUBLE COMMENT '预计负债',
# 	lease_libilities DOUBLE COMMENT '租赁负债',
# 	total_current_liab DOUBLE COMMENT '流动负债合计',
# 	total_liab DOUBLE COMMENT '负债合计',
# )COMMENT='资产负债表' DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE=InnoDB
# CREATE TABLE basic_info_CN_STOCK_A (
# 	instrument VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL COMMENT '证券代码',
# 	company_name VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci COMMENT '公司名称',
#     name VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci COMMENT '证券名称',
# )COMMENT='A股股票基本信息' DEFAULT CHARSET=utf8mb3 ENGINE=InnoDB
# CREATE TABLE cash_flow_CN_STOCK_A (
# 	report_date DATE COMMENT '报告期',
# )COMMENT='现金流量表' DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE=InnoDB
# CREATE TABLE income_CN_STOCK_A (
# 	date DATE COMMENT '日期',
# 	report_date DATE COMMENT '报告期',
# 	charge_and_commi_expenses DOUBLE COMMENT '手续费及佣金支出',
# 	fee_and_commi_income DOUBLE COMMENT '手续费及佣金收入',
# )COMMENT='利润表' DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE=InnoDB
# """
# fk_str = ""
# example_values = """
# {
#     'basic_info_CN_STOCK_A.instrument': ['002089.SZA', '002543.SZA', '300081.SZ', '688056.SHA', '603887.SHA', '830946.BJA', '832786.BJA', '000787.SZA'],
#     'basic_info_CN_STOCK_A.company_name': ["珠海格力电器股份有限公司", "比亚迪股份有限公司", "平安银行股份有限公司", "华夏银行股份有限公司", "中国平安股份有限公司", "四川长虹新能源科技股份有限公司", "同享(苏州)电子材料科技股份有限公司", "东华能源股份有限公司", "同兴环保科技股份有限公司"],
#     'basic_info_CN_STOCK_A.name': ['平安银行', '格力电器', '比亚迪', '长虹能源', '华夏银行', '中国平安', '同享科技', '东华能源', '同兴环保'],
# }"""
# query = "2022年工商银行的现金等价物的期末余额是多少？"

# prompt = new_decompose_template.format(
#     db_type='mysql', desc_str=desc_str, fk_str=fk_str, example_values=example_values, query=query)
# print(prompt)

new_decompose_template_example = """
Given a 【Database schema】 description,【Example values】 and the 【Question】, you need to use valid mysql and understand the database and knowledge, and then decompose the question into subquestions for text-to-SQL generation.
When generating SQL, we should always consider constraints:
【Constraints】
- In `SELECT <column>`, just select needed columns in the 【Question】 without any unnecessary column or value
- In `FROM <table>` or `JOIN <table>`, do not include unnecessary table
- If use max or min func, `JOIN <table>` FIRST, THEN use `SELECT MAX(<column>)` or `SELECT MIN(<column>)`
- If [Value examples] of <column> has 'None' or None, use `JOIN <table>` or `WHERE <column> is NOT NULL` is better
- If use `ORDER BY <column> ASC|DESC`, add `GROUP BY <column>` before to select distinct values
- Use `LIMIT` to restrict the number of rows returned when necessary
- Pelase make sure the selected columns are existing in the corresponding tables.
- Please use the original Chinese company_name and company_province in the SQL query, rather than translating them into English.
- Please make sure the generated SQL is compatible with the mysql database.
- When generating SQL for sub questions, if the subsequent sub questions need to use the SQL generated by the previous sub questions, please use the previously generated SQL in the subquery or JOIN operation, and do not assume any query results.

==========

【Database schema】
CREATE TABLE frpm (
    CDSCode VARCHAR(50) PRIMARY KEY COMMENT CDSCode
    Charter School (Y/N) COMMENT 0: N; 1: Y
    Enrollment (Ages 5-17) FLOAT COMMENT Enrollment (Ages 5-17)
    Free Meal Count (Ages 5-17) FLOAT COMMENT Free Meal Count (Ages 5-17)
    FOREIGN KEY (CDSCode) REFERENCES satscores(cds)
);

CREATE TABLE satscores (
    cds VARCHAR(50) PRIMARY KEY COMMENT California Department Schools
    sname VARCHAR(50) COMMENT school name
    NumTstTakr INT COMMENT number of test takers in each school
    AvgScrMath INT COMMENT average scores in Math
    NumGE1500 INT COMMENT Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500
);

【Foreign keys】
frpm: ['frpm.CDSCode=satscores.cds']

【Example values】
{
    'frpm.CDSCode': ['01000000000000', '01000000000001', '01000000000002', '01000000000003', '01000000000004'],
    'frpm.Charter School (Y/N)': [0, 1, 0, 1, 0],
    'frpm.Enrollment (Ages 5-17)': [100, 200, 300, 400, 500],
    'frpm.Free Meal Count (Ages 5-17)': [10, 20, 30, 40, 50],
}

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
    account_id INT PRIMARY KEY COMMENT the id of the account
    district_id INT COMMENT location of branch
    frequency VARCHAR(50) COMMENT frequency of the acount
    date DATE COMMENT the creation date of the account
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

CREATE TABLE client (
    client_id INT PRIMARY KEY COMMENT the unique number
    gender CHAR(1) COMMENT gender. F: female . M: male
    birth_date DATE COMMENT birth date
    district_id INT COMMENT location of branch
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

CREATE TABLE district (
    district_id INT PRIMARY KEY COMMENT location of branch
    A4 INT COMMENT number of inhabitants
    A11 INT COMMENT average salary
);

【Foreign keys】
client: ['client.district_id = district.district_id']
account: ['account.district_id = district.district_id']

【Example values】
{
    'account.account_id': [1, 2, 3, 4, 5],
    'account.district_id': [1, 2, 3, 4, 5],
    'account.frequency': ['monthly', 'monthly', 'monthly', 'monthly', 'monthly'],
    'account.date': [2020-01-01, 2020-01-01, 2020-01-01, 2020-01-01, 2020-01-01],
    'client.client_id': [1, 2, 3, 4, 5],
}

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
CREATE TABLE balance_sheet_CN_STOCK_A (
	instrument VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '股票代码', 
	report_date DATE NOT NULL COMMENT '报告期', 
	charge_and_commi_payable DOUBLE COMMENT '应付手续费及佣金', 
	contract_liab DOUBLE COMMENT '合同负债', 
	estimated_liab DOUBLE COMMENT '预计负债', 
	lease_libilities DOUBLE COMMENT '租赁负债', 
	total_current_liab DOUBLE COMMENT '流动负债合计', 
	total_liab DOUBLE COMMENT '负债合计', 
)COMMENT='资产负债表' DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE=InnoDB
CREATE TABLE basic_info_CN_STOCK_A (
	instrument VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL COMMENT '证券代码', 
	company_name VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci COMMENT '公司名称',
    name VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci COMMENT '证券名称', 
)COMMENT='A股股票基本信息' DEFAULT CHARSET=utf8mb3 ENGINE=InnoDB
CREATE TABLE cash_flow_CN_STOCK_A (
	report_date DATE COMMENT '报告期', 
)COMMENT='现金流量表' DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE=InnoDB
CREATE TABLE income_CN_STOCK_A (
	date DATE COMMENT '日期', 
	report_date DATE COMMENT '报告期', 
	charge_and_commi_expenses DOUBLE COMMENT '手续费及佣金支出', 
	fee_and_commi_income DOUBLE COMMENT '手续费及佣金收入', 
)COMMENT='利润表' DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE=InnoDB

【Foreign keys】
None

【Example values】
{
    'basic_info_CN_STOCK_A.instrument': ['002089.SZA', '002543.SZA', '300081.SZ', '688056.SHA', '603887.SHA', '830946.BJA', '832786.BJA', '000787.SZA'],
    'basic_info_CN_STOCK_A.company_name': ["珠海格力电器股份有限公司", "比亚迪股份有限公司", "平安银行股份有限公司", "华夏银行股份有限公司", "中国平安股份有限公司", "四川长虹新能源科技股份有限公司", "同享(苏州)电子材料科技股份有限公司", "东华能源股份有限公司", "同兴环保科技股份有限公司"],
    'basic_info_CN_STOCK_A.name': ['平安银行', '格力电器', '比亚迪', '长虹能源', '华夏银行', '中国平安', '同享科技', '东华能源', '同兴环保'],
}

【Question】
2022年科大讯飞和华泰科技哪家公司的手续费及佣金支出更多？

【Solution】
Decompose the question into sub questions, based on the given 【Database schema】, 【Constraints】, and 【Example values】, and generate the SQL after thinking step by step:

"""

build_question_template = """
给定如下数据库结构和一些数值样例，请构建五十个问题，要求问题的答案可以从数据库中找到。构建问题时请参考以下要求：
1. 问题的答案可以从数据库中找到。
2. 问题的答案是具体的数值或实体，而不是开放性问题。
3. 问题的答案可以通过单个SQL查询或多个SQL查询获得。
4. 请参考给定的数据库结构， 并尽可能利用每一个给定的数值样例构建问题。
5. 只需要构建问题, 不需要提供解释或者SQL查询。

【数据库结构】
CREATE TABLE `balance_sheet_CN_STOCK_A` (
    date DATE NOT NULL COMMENT '公告日',
    instrument VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '股票代码',
    report_date DATE NOT NULL COMMENT '报告期',
    change_type INTEGER COMMENT '调整类型 0：未调整，1：调整过',
    fs_quarter_index INTEGER COMMENT '对应季度',
    account_receivable DOUBLE COMMENT '应收账款',
    accounts_payable DOUBLE COMMENT '应付账款',
    act_underwriting_sec DOUBLE COMMENT '代理承销证券款',
    acting_td_sec DOUBLE COMMENT '代理买卖证券款',
    actual_received_capital DOUBLE COMMENT '实收资本（或股本）',
    advance_payment DOUBLE COMMENT '预收款项',
    appropriative_reserve DOUBLE COMMENT '专项储备',
    asset_diff_sri DOUBLE COMMENT '资产差额（特殊报表科目）',
    asset_diff_tbi DOUBLE COMMENT '资产差额（合计平衡科目）',
    bill_and_account_payable DOUBLE COMMENT '应付票据及应付账款',
    bill_and_account_receivable DOUBLE COMMENT '应收票据及应收账款',
    bill_payable DOUBLE COMMENT '应付票据',
    bill_receivable DOUBLE COMMENT '应收票据',
    bond_payable DOUBLE COMMENT '应付债券',
    borrowing_funds DOUBLE COMMENT '拆入资金',
    bs_other_compre_income DOUBLE COMMENT '其他综合收益',
    buy_resale_fnncl_assets DOUBLE COMMENT '买入返售金融资产',
    capital_reserve DOUBLE COMMENT '资本公积',
    charge_and_commi_payable DOUBLE COMMENT '应付手续费及佣金',
    construction_in_process DOUBLE COMMENT '在建工程',
    construction_in_process_sum DOUBLE COMMENT '在建工程合计',
    contract_asset DOUBLE COMMENT '合同资产',
    contract_liab DOUBLE COMMENT '合同负债',
    currency_fund DOUBLE COMMENT '货币资金',
    debt_right_invest DOUBLE COMMENT '债权投资',
    derivative_fnncl_assets DOUBLE COMMENT '衍生金融资产',
    derivative_fnncl_liab DOUBLE COMMENT '衍生金融负债',
    dev_expenditure DOUBLE COMMENT '开发支出',
    differed_income_current_liab DOUBLE COMMENT '递延收益-流动负债',
    differed_incomencl DOUBLE COMMENT '递延收益-非流动负债',
    divided_into_asset_for_sale DOUBLE COMMENT '持有待售资产',
    divided_into_liab_for_sale DOUBLE COMMENT '持有待售负债',
    dividend_payable DOUBLE COMMENT '应付股利',
    dividend_receivable DOUBLE COMMENT '应收股利',
    dt_assets DOUBLE COMMENT '递延所得税资产',
    dt_liab DOUBLE COMMENT '递延所得税负债',
    earned_surplus DOUBLE COMMENT '盈余公积',
    equity_right_diff_tbi DOUBLE COMMENT '股权权益差额（合计平衡科目）',
    estimated_liab DOUBLE COMMENT '预计负债',
    fa_calc_by_amortized_cost DOUBLE COMMENT '以摊余成本计量的金融资产',
    fixed_asset DOUBLE COMMENT '固定资产',
    fixed_asset_sum DOUBLE COMMENT '固定资产合计',
    fixed_assets_disposal DOUBLE COMMENT '固定资产清理',
    flow_assets_diff_sri DOUBLE COMMENT '流动资产差额（特殊报表科目）',
    flow_assets_diff_tbi DOUBLE COMMENT '流动资产差额（合计平衡科目）',
    flow_debt_diff_sri DOUBLE COMMENT '流动负债差额（特殊报表科目）',
    flow_debt_diff_tbi DOUBLE COMMENT '流动负债差额（合计平衡科目）',
    fnncl_assets_sold_for_repur DOUBLE COMMENT '卖出回购金融资产款',
    frgn_currency_convert_diff DOUBLE COMMENT '外币报表折算差额',
    general_risk_provision DOUBLE COMMENT '一般风险准备',
    goodwill DOUBLE COMMENT '商誉',
    held_to_maturity_invest DOUBLE COMMENT '持有至到期投资',
    holder_equity_diff_sri DOUBLE COMMENT '股东权益差额（特殊报表科目）',
    insurance_contract_reserve DOUBLE COMMENT '保险合同准备金',
    intangible_assets DOUBLE COMMENT '无形资产',
    interest_payable DOUBLE COMMENT '应付利息',
    interest_receivable DOUBLE COMMENT '应收利息',
    inventory DOUBLE COMMENT '存货',
    invest_property DOUBLE COMMENT '投资性房地产',
    lease_libilities DOUBLE COMMENT '租赁负债',
    lending_fund DOUBLE COMMENT '拆出资金',
    liab_and_equity_diff_sri DOUBLE COMMENT '负债及股东权益差额（特殊报表科目）',
    liab_and_equity_diff_tbi DOUBLE COMMENT '负债及股东权益差额（合计平衡科目）',
    liab_diff_sri DOUBLE COMMENT '负债差额（特殊报表科目）',
    liab_diff_tbi DOUBLE COMMENT '负债差额（合计平衡科目）',
    loan_from_central_bank DOUBLE COMMENT '向中央银行借款',
    loans_and_payments DOUBLE COMMENT '发放贷款及垫款',
    `It_deferred_expense` DOUBLE COMMENT '长期待摊费用',
    `It_equity_invest` DOUBLE COMMENT '长期股权投资',
    `It_loan` DOUBLE COMMENT '长期借款',
    `It_payable` DOUBLE COMMENT '长期应付款',
    `It_payable_sum` DOUBLE COMMENT '长期应付款合计',
    `It_receivable` DOUBLE COMMENT '长期应收款',
    `It_staff_salary_payable` DOUBLE COMMENT '长期应付职工薪酬',
    minority_equity DOUBLE COMMENT '少数股东权益',
    noncurrent_asset_due_within1y DOUBLE COMMENT '一年内到期的非流动资产',
    noncurrent_assets_diff_sri DOUBLE COMMENT '非流动资产差额（特殊报表科目）',
    noncurrent_assets_diff_tbi DOUBLE COMMENT '非流动资产差额（合计平衡科目）',
    noncurrent_liab_diff_sbi DOUBLE COMMENT '非流动负债差额（合计平衡科目）',
    noncurrent_liab_diff_sri DOUBLE COMMENT '非流动负债差额（特殊报表科目）',
    noncurrent_liab_due_in1y DOUBLE COMMENT '一年内到期的非流动负债',
    oil_and_gas_asset DOUBLE COMMENT '油气资产',
    other_compre_fa_by_fv DOUBLE COMMENT '以公允价值计量且其变动计入其他综合收益的金融资产',
    other_cunrren_assets DOUBLE COMMENT '其他流动资产',
    other_current_liab DOUBLE COMMENT '其他流动负债',
    other_debt_right_invest DOUBLE COMMENT '其他债权投资',
    other_ei_invest DOUBLE COMMENT '其他权益工具投资',
    other_equity_instruments DOUBLE COMMENT '其他权益工具',
    other_payables DOUBLE COMMENT '其他应付款',
    other_payables_sum DOUBLE COMMENT '其他应付款合计',
    other_receivables DOUBLE COMMENT '其他应收款',
    other_receivables_sum DOUBLE COMMENT '其他应收款合计',
    other_uncurrent_fa DOUBLE COMMENT '其他非流动金融资产',
    othr_noncurrent_assets DOUBLE COMMENT '其他非流动资产',
    othr_noncurrent_liab DOUBLE COMMENT '其他非流动负债',
    payroll_payable DOUBLE COMMENT '应付职工薪酬',
    perpetual_capital_sec DOUBLE COMMENT '永续债',
    preferred_shares DOUBLE COMMENT '其中优先股',
    preferred DOUBLE COMMENT '优先股',
    premium_receivable DOUBLE COMMENT '应收保费',
    prepays DOUBLE COMMENT '预付款项',
    productive_biological_assets DOUBLE COMMENT '生产性生物资产',
    project_goods_and_material DOUBLE COMMENT '工程物资',
    receivable_financing DOUBLE COMMENT '应收款项融资',
    rein_account_receivable DOUBLE COMMENT '应收分保账款',
    rein_contract_reserve DOUBLE COMMENT '应收分保合同准备金',
    rein_payable DOUBLE COMMENT '应付分保账款',
    right_of_use_assets DOUBLE COMMENT '使用权资产',
    saleable_finacial_assets DOUBLE COMMENT '可供出售金融资产',
    saving_and_interbank_deposit DOUBLE COMMENT '吸收存款及同业存放',
    settle_reserves DOUBLE COMMENT '结算备付金',
    special_payable DOUBLE COMMENT '专项应付款',
    st_bond_payable DOUBLE COMMENT '应付短期债券',
    st_borrow DOUBLE COMMENT '短期借款',
    tax_payable DOUBLE COMMENT '应交税费',
    total_assets DOUBLE COMMENT '资产总计',
    total_current_assets DOUBLE COMMENT '流动资产合计',
    total_current_liab DOUBLE COMMENT '流动负债合计',
    total_equity_atoopc DOUBLE COMMENT '归属于母公司所有者权益合计',
    total_liab_and_owner_equity DOUBLE COMMENT '负债和所有者权益总计',
    total_liab DOUBLE COMMENT '负债合计',
    total_noncurrent_assets DOUBLE COMMENT '非流动资产合计',
    total_noncurrent_liab DOUBLE COMMENT '非流动负债合计',
    total_owner_equity DOUBLE COMMENT '所有者权益合计',
    tradable_fnncl_assets DOUBLE COMMENT '交易性金融资产',
    tradable_fnncl_liab DOUBLE COMMENT '交易性金融负债',
    treasury_stock DOUBLE COMMENT '库存股',
    undstrbtd_profit DOUBLE COMMENT '未分配利润',
    PRIMARY KEY (date, instrument, report_date)
) COLLATE utf8mb4_unicode_ci ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '资产负债表'

CREATE TABLE `basic_info_CN_STOCK_A` (
    instrument VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL COMMENT '证券代码',
    delist_date DATE COMMENT '退市日期，如果未退市，则为pandas.NaT',
    company_type VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci COMMENT '公司类型',
    company_name VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci COMMENT '公司名称',
    company_province VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci COMMENT '公司省份',
    list_board VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci COMMENT '上市板',
    company_found_date DATETIME COMMENT '公司成立日期',
    name VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci COMMENT '证券名称',
    list_date DATE COMMENT '上市日期',
    PRIMARY KEY (instrument)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb3 COMMENT = 'A股股票基本信息'

CREATE TABLE `cash_flow_CN_STOCK_A` (
    date DATE COMMENT '公告日',
    instrument VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '股票代码',
    report_date DATE COMMENT '报告期',
    change_type INTEGER COMMENT '调整类型 0：未调整，1：调整过',
    fs_quarter_index INTEGER COMMENT '对应季度',
    asset_impairment_reserve DOUBLE COMMENT '资产减值准备',
    borrowing_net_add_central_bank DOUBLE COMMENT '向中央银行借款净增加额',
    borrowing_net_increase_amt DOUBLE COMMENT '拆入资金净增加额',
    cash_of_orig_ic_indemnity DOUBLE COMMENT '支付原保险合同赔付款项的现金',
    cash_paid_for_assets DOUBLE COMMENT '购建固定资产、无形资产和其他长期资产支付的现金',
    cash_paid_for_interests_etc DOUBLE COMMENT '支付利息、手续费及佣金的现金',
    cash_paid_for_pd DOUBLE COMMENT '支付保单红利的现金',
    cash_paid_of_distribution DOUBLE COMMENT '分配股利、利润或偿付利息支付的现金',
    cash_paid_to_staff_etc DOUBLE COMMENT '支付给职工以及为职工支付的现金',
    cash_pay_for_debt DOUBLE COMMENT '偿还债务支付的现金',
    cash_received_from_bond_issue DOUBLE COMMENT '发行债券收到的现金',
    cash_received_from_orig_ic DOUBLE COMMENT '收到原保险合同保费取得的现金',
    cash_received_of_absorb_invest DOUBLE COMMENT '吸收投资收到的现金',
    cash_received_of_borrowing DOUBLE COMMENT '取得借款收到的现金',
    cash_received_of_dspsl_invest DOUBLE COMMENT '收回投资收到的现金',
    cash_received_of_interest_etc DOUBLE COMMENT '收取利息、手续费及佣金的现金',
    cash_received_of_other_fa DOUBLE COMMENT '收到其他与投资活动有关的现金',
    cash_received_of_other_oa DOUBLE COMMENT '收到其他与经营活动有关的现金',
    cash_received_of_othr_fa DOUBLE COMMENT '收到其他与筹资活动有关的现金',
    cash_received_of_sales_service DOUBLE COMMENT '销售商品、提供劳务收到的现金',
    cb_due_within1y DOUBLE COMMENT '一年内到期的可转换公司债券',
    cce_net_add_amt_diff_sri_dm DOUBLE COMMENT '直接法—现金及现金等价物净增加额差额（特殊报表科目）',
    cce_net_add_amt_diff_tbi_dm DOUBLE COMMENT '直接法—现金及现金等价物净增加额差额（合计平衡科目）',
    cce_net_add_diff_im_sri DOUBLE COMMENT '间接法—现金及现金等价物净增加额差额（特殊报表科目）',
    cce_net_add_diff_im_tbi DOUBLE COMMENT '间接法—现金及现金等价物净增加额差额（合计平衡科目）',
    cr_from_minority_holders DOUBLE COMMENT '子公司吸收少数股东投资收到的现金',
    credit_impairment_loss DOUBLE COMMENT '信用减值损失',
    dap_paid_to_minority_holder DOUBLE COMMENT '子公司支付给少数股东的股利、利润',
    debt_tranfer_to_capital DOUBLE COMMENT '债务转为资本',
    deposit_and_interbank_net_add DOUBLE COMMENT '客户存款和同业存放款项净增加额',
    depreciation_etc DOUBLE COMMENT '固定资产折旧、油气资产折耗、生产性生物资产折旧',
    dt_assets_decrease DOUBLE COMMENT '递延所得税资产减少',
    dt_liab_increase DOUBLE COMMENT '递延所得税负债增加',
    effect_of_exchange_chg_on_cce DOUBLE COMMENT '汇率变动对现金及现金等价物的影响',
    ending_balance_of_cash DOUBLE COMMENT '现金的期末余额',
    fa_cash_in_flow_diff_sri DOUBLE COMMENT '筹资活动现金流入差额（特殊报表科目）',
    fa_cash_in_flow_diff_tbi DOUBLE COMMENT '筹资活动现金流入差额（合计平衡科目）',
    fa_cash_out_flow_diff_sri DOUBLE COMMENT '筹资活动现金流出差额（特殊报表科目）',
    fa_cash_out_flow_diff_tbi DOUBLE COMMENT '筹资活动现金流出差额（合计平衡科目）',
    final_balance_of_cce DOUBLE COMMENT '期末现金及现金等价物余额',
    finance_cost_cfs DOUBLE COMMENT '现金流量表—财务费用',
    finance_lease_fixed_assets DOUBLE COMMENT '融资租入固定资产',
    fixed_assets_scrap_loss DOUBLE COMMENT '固定资产报废损失',
    goods_buy_and_service_cash_pay DOUBLE COMMENT '购买商品、接受劳务支付的现金',
    ia_cash_inflow_diff_sri DOUBLE COMMENT '投资活动现金流入差额（特殊报表科目）',
    ia_cash_inflow_diff_tbi DOUBLE COMMENT '投资活动现金流入差额（合计平衡科目）',
    ia_cash_outflow_diff_sri DOUBLE COMMENT '投资活动现金流出差额（特殊报表科目）',
    ia_cash_outflow_diff_tbi DOUBLE COMMENT '投资活动现金流出差额（合计平衡科目）',
    increase_of_operating_item DOUBLE COMMENT '经营性应付项目的增加',
    initial_balance_of_cash DOUBLE COMMENT '现金的期初余额',
    initial_balance_of_cce DOUBLE COMMENT '现金等价物的期初余额',
    initial_cce_balance DOUBLE COMMENT '期初现金及现金等价物余额',
    intangible_assets_amortized DOUBLE COMMENT '无形资产摊销',
    inventory_decrease DOUBLE COMMENT '存货的减少',
    invest_income_cash_received DOUBLE COMMENT '取得投资收益收到的现金',
    invest_loss DOUBLE COMMENT '投资损失',
    invest_paid_cash DOUBLE COMMENT '投资支付的现金',
    lending_net_add_other_org DOUBLE COMMENT '向其他金融机构拆入资金净增加额',
    loan_and_advancenet_add DOUBLE COMMENT '客户贷款及垫款净增加额',
    loss_from_fv_chg DOUBLE COMMENT '公允价值变动损失',
    loss_of_disposal_assets DOUBLE COMMENT '处置固定资产、无形资产和其他长期资产的损失',
    `It_deferred_expenses_amrtzt` DOUBLE COMMENT '长期待摊费用摊销',
    naa_of_cb_and_interbank DOUBLE COMMENT '存放中央银行和同业款项净增加额',
    naa_of_disposal_fnncl_assets DOUBLE COMMENT '处置以公允价值计量且其变动计入当期损益的金融资产净增加额',
    naaassured_saving_and_invest DOUBLE COMMENT '保户储金及投资款净增加额',
    ncf_diff_from_fa_sri DOUBLE COMMENT '筹资活动产生的现金流量净额差额（特殊报表科目）',
    ncf_diff_from_fa_tbi DOUBLE COMMENT '筹资活动产生的现金流量净额差额（合计平衡科目）',
    ncf_diff_from_ia_sri DOUBLE COMMENT '投资活动产生的现金流量净额差额（特殊报表科目）',
    ncf_diff_from_ia_tbi DOUBLE COMMENT '投资活动产生的现金流量净额差额（合计平衡科目）',
    ncf_diff_from_oa_im_sri DOUBLE COMMENT '间接法—经营活动现金流量净额差额（特殊报表科目）',
    ncf_diff_from_oa_im_tbi DOUBLE COMMENT '间接法—经营活动现金流量净额差额（合计平衡科目）',
    ncf_diff_of_oa_sri DOUBLE COMMENT '经营活动产生的现金流量净额差额（特殊报表科目）',
    ncf_diff_of_oa_tbi DOUBLE COMMENT '经营活动产生的现金流量净额差额（合计平衡科目）',
    ncf_from_fa DOUBLE COMMENT '筹资活动产生的现金流量净额',
    ncf_from_ia DOUBLE COMMENT '投资活动产生的现金流量净额',
    ncf_from_oa_im DOUBLE COMMENT '间接法—经营活动产生的现金流量净额',
    ncf_from_oa DOUBLE COMMENT '经营活动产生的现金流量净额',
    net_add_in_pledge_loans DOUBLE COMMENT '质押贷款净增加额',
    net_add_in_repur_capital DOUBLE COMMENT '回购业务资金净增加额',
    net_cash_amt_from_branch DOUBLE COMMENT '取得子公司及其他营业单位支付的现金净额',
    net_cash_of_disposal_assets DOUBLE COMMENT '处置固定资产、无形资产和其他长期资产收回的现金净额',
    net_cash_of_disposal_branch DOUBLE COMMENT '处置子公司及其他营业单位收到的现金净额',
    net_cash_received_from_rein DOUBLE COMMENT '收到再保业务现金净额',
    net_increase_in_cce_im DOUBLE COMMENT '间接法—现金及现金等价物净增加额',
    net_increase_in_cce DOUBLE COMMENT '现金及现金等价物净增加额',
    np_cfs DOUBLE COMMENT '现金流量表-净利润',
    oa_cash_inflow_diff_sri DOUBLE COMMENT '经营活动现金流入差额（特殊报表科目）',
    oa_cash_inflow_diff_tbi DOUBLE COMMENT '经营活动现金流入差额（合计平衡科目）',
    oa_cash_outflow_diff_sri DOUBLE COMMENT '经营活动现金流出差额（特殊报表科目）',
    oa_cash_outflow_diff_tbi DOUBLE COMMENT '经营活动现金流出差额（合计平衡科目）',
    operating_items_decrease DOUBLE COMMENT '经营性应收项目的减少',
    other_cash_paid_related_to_ia DOUBLE COMMENT '支付其他与投资活动有关的现金',
    other_cash_paid_related_to_oa DOUBLE COMMENT '支付其他与经营活动有关的现金',
    othrcash_paid_relating_to_fa DOUBLE COMMENT '支付其他与筹资活动有关的现金',
    payments_of_all_taxes DOUBLE COMMENT '支付的各项税费',
    refund_of_tax_and_levies DOUBLE COMMENT '收到的税费返还',
    si_final_balance_of_cce DOUBLE COMMENT '现金等价物的期末余额',
    si_other DOUBLE COMMENT '其他',
    sub_total_of_ci_from_fa DOUBLE COMMENT '筹资活动现金流入小计',
    sub_total_of_ci_from_ia DOUBLE COMMENT '投资活动现金流入小计',
    sub_total_of_ci_from_oa DOUBLE COMMENT '经营活动现金流入小计',
    sub_total_of_cos_from_fa DOUBLE COMMENT '筹资活动现金流出小计',
    sub_total_of_cos_from_ia DOUBLE COMMENT '投资活动现金流出小计',
    sub_total_of_cos_from_oa DOUBLE COMMENT '经营活动现金流出小计'
) COLLATE utf8mb4_unicode_ci ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '现金流量表'

CREATE TABLE `income_CN_STOCK_A` (
    date DATE COMMENT '日期',
    instrument VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '股票代码',
    report_date DATE COMMENT '报告期',
    change_type INTEGER COMMENT '调整类型 (0: 未调整, 1: 调整过)',
    fs_quarter_index INTEGER COMMENT '对应季度',
    amortized_cost_fnncl_ass_cfrm DOUBLE COMMENT '以摊余成本计量的金融资产终止确认收益',
    asset_change_due_to_remeasure DOUBLE COMMENT '重新计量设定受益计划净负债或净资产的变动',
    asset_disposal_gain DOUBLE COMMENT '资产处置收益',
    asset_impairment_loss DOUBLE COMMENT '资产减值损失',
    basic_eps DOUBLE COMMENT '基本每股收益',
    cannt_reclass_gal_equity_law DOUBLE COMMENT '权益法下在被投资单位不能重分类进损益的其他综合收益中享有的份额',
    cannt_reclass_to_gal DOUBLE COMMENT '以后不能重分类进损益的其他综合收益',
    cash_flow_hedge_reserve DOUBLE COMMENT '现金流量套期储备',
    cf_hedging_gal_valid_part DOUBLE COMMENT '现金流量套期损益的有效部分',
    charge_and_commi_expenses DOUBLE COMMENT '手续费及佣金支出',
    commi_on_insurance_policy DOUBLE COMMENT '保单红利支出',
    compensate_net_pay DOUBLE COMMENT '赔付支出净额',
    continued_operating_np DOUBLE COMMENT '（一）持续经营净利润',
    corp_credit_risk_fvc DOUBLE COMMENT '企业自身信用风险公允价值变动',
    credit_impairment_loss DOUBLE COMMENT '信用减值损失',
    dlt_earnings_per_share DOUBLE COMMENT '稀释每股收益',
    earned_premium DOUBLE COMMENT '已赚保费',
    exchange_gain DOUBLE COMMENT '汇兑收益',
    extract_ic_reserve_net_amt DOUBLE COMMENT '提取保险合同准备金净额',
    fa_reclassi_amt DOUBLE COMMENT '金融资产重分类计入其他综合收益的金额',
    fc_convert_diff DOUBLE COMMENT '外币财务报表折算差额',
    fc_interest_income DOUBLE COMMENT '财务费用：利息收入',
    fee_and_commi_income DOUBLE COMMENT '手续费及佣金收入',
    financing_expenses DOUBLE COMMENT '财务费用',
    fv_chg_income DOUBLE COMMENT '公允价值变动收益',
    ii_from_jc_etc DOUBLE COMMENT '对联营企业和合营企业的投资收益',
    income_tax_cost DOUBLE COMMENT '所得税费用',
    interest_fee DOUBLE COMMENT '财务费用：利息费用',
    interest_income DOUBLE COMMENT '利息收入',
    interest_payout DOUBLE COMMENT '利息支出',
    invest_income DOUBLE COMMENT '投资收益',
    manage_fee DOUBLE COMMENT '管理费用',
    minority_gal DOUBLE COMMENT '少数股东损益',
    net_open_hedge_income DOUBLE COMMENT '净敞口套期收益',
    non_operating_income DOUBLE COMMENT '营业外收入',
    noncurrent_asset_dispose_gain DOUBLE COMMENT '非流动资产处置利得',
    noncurrent_asset_dispose_loss DOUBLE COMMENT '非流动资产处置损失',
    nonoperating_cost DOUBLE COMMENT '营业外支出',
    np_atoopc DOUBLE COMMENT '归属于母公司所有者的净利润',
    np_diff_sri DOUBLE COMMENT '净利润差额（特殊报表科目）',
    np_diff_tbi DOUBLE COMMENT '净利润差额（合计平衡科目）',
    op_diff_sri DOUBLE COMMENT '营业利润差额（特殊报表科目）',
    op_diff_tbi DOUBLE COMMENT '营业利润差额（合计平衡科目）',
    operating_cost_diff_sri DOUBLE COMMENT '营业支出（特殊报表科目）',
    operating_cost_diff_tbi DOUBLE COMMENT '营业支出（合计平衡项目）',
    operating_cost DOUBLE COMMENT '营业成本',
    operating_revenue_diff_sri DOUBLE COMMENT '营业收入（特殊报表科目）',
    operating_revenue_diff_tbi DOUBLE COMMENT '营业收入（合计平衡项目）',
    operating_taxes_and_surcharge DOUBLE COMMENT '税金及附加',
    operating_total_cost DOUBLE COMMENT '营业总成本',
    operating_total_revenue DOUBLE COMMENT '营业总收入',
    other_compre_income DOUBLE COMMENT '其他综合收益',
    other_debt_right_invest_fvc DOUBLE COMMENT '其他债权投资公允价值变动',
    other_debt_right_invest_ir DOUBLE COMMENT '其他债权投资信用减值准备',
    other_equity_invest_fvc DOUBLE COMMENT '其他权益工具投资公允价值变动',
    other_income DOUBLE COMMENT '其他收益',
    other_not_reclass_to_gal DOUBLE COMMENT '其他以后不能重分类进损益',
    other_reclass_to_gal DOUBLE COMMENT '其他以后将重分类进损益',
    othrcompre_income_atms DOUBLE COMMENT '归属于少数股东的其他综合收益',
    othrcompre_income_atoopc DOUBLE COMMENT '归属母公司所有者的其他综合收益',
    rad_cost_sum DOUBLE COMMENT '研发费用',
    reclass_and_salable_gal DOUBLE COMMENT '持有至到期投资重分类为可供出售金融资产损益',
    reclass_to_gal DOUBLE COMMENT '以后将重分类进损益的其他综合收益',
    reclass_togal_in_equity_law DOUBLE COMMENT '权益法下在被投资单位以后将重分类进损益的其他综合收益中享有的份额',
    refunded_premium DOUBLE COMMENT '退保金',
    rein_expenditure DOUBLE COMMENT '分保费用',
    revenue DOUBLE COMMENT '营业收入',
    saleable_fv_chg_gal DOUBLE COMMENT '可供出售金融资产公允价值变动损益',
    sales_fee DOUBLE COMMENT '销售费用',
    stop_operating_np DOUBLE COMMENT '（二）终止经营净利润',
    total_compre_income_atsopc DOUBLE COMMENT '归属于母公司股东的综合收益总额',
    total_compre_income DOUBLE COMMENT '综合收益总额',
    total_profit_diff_sri DOUBLE COMMENT '利润总额差额（特殊报表科目）',
    total_profit_diff_tbi DOUBLE COMMENT '利润总额差额（合计平衡科目）',
    total_profit DOUBLE COMMENT '利润总额'
) COLLATE utf8mb4_unicode_ci ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '利润表'

【数值样例】
{
    'instrument': ['002089.SZA', '002543.SZA', '300081.SZ', '688056.SHA', '603887.SHA', '830946.BJA', '832786.BJA', '000787.SZA'],
    'company_type': ['中外合资企业', '中央国有企业', '公众企业', '其他企业', '地方国有企业', '外资企业', '民营企业', '集体企业'],
    'company_name': ['一汽解放集团股份有限公司', 'TCL科技集团股份有限公司', '万科企业股份有限公司', '中国石油天然气股份有限公司', '中国石油化工股份有限公司', '重庆长安汽车股份有限公司', '银座集团股份有限公司', '中国银行股份有限公司', '金融街控股股份有限公司', '中国中铁股份有限公司', '长春吉大正元信息技术股份有限公司', '中国中车股份有限公司', '鲁西化工集团股份有限公司', '苏州锴威特半导体股份有限公司', '中国中化股份有限公司', '西安宝德自动化股份有限公司', '中国中信股份有限公司'],
    'company_province': ['上海', '云南省', '内蒙古自治区', '北京', '吉林省', '四川省', '天津', '宁夏回族自治区', '安徽省', '山东省', '山西省', '广东省', '广西壮族自治区', '新疆维吾尔自治区', '江苏省', '江西省', '河北省', '河南省', '浙江省', '海南省', '湖北省', '湖南省', '甘肃省', '福建省', '西藏自治区', '贵州省', '辽宁省', '重庆', '陕西省', '青海省', '黑龙江省']
    'list_board': ['主板', '创业板', '北证', '科创板'],
    'name': ['平安银行', '万科A', '国农科技', '深振业A', '神州高铁', '中国宝安', '特力A', '大冶特钢', '华发股份', '四川长虹', '新希望', '天山股份', '云南铜业', '潍柴重机', '中广核技', '华联股份', '湖北能源', '城发环境', '海南高速', '中鼎股份', '峨眉山A', 'ST中嘉', '法尔胜', '欢瑞世纪', '亚钾国际']
}

【规则】
1. 问题的答案可以从数据库中找到。
2. 问题的答案是具体的数值或实体，而不是开放性问题。
3. 问题的答案可以通过单个SQL查询或多个SQL查询获得。
4. 问题中应该利用提供的数值样例。
5. 只需要构建问题, 不需要提供解释或者SQL查询。

【问题】
"""
