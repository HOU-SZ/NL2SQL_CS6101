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
12) If the question is asking for a value or statistic of the value, please return the sum or difference according to the question. For example, if the question is "2022年晨光文具的筹资活动现金流出小计是多少？", you need to return the sum of the corresponding column: SELECT SUM(sub_total_of_cos_from_fa) FROM cash_flow_CN_STOCK_A"
13) If the question is asking for a value at a specific year, please use the date column to filter the data. For example, if the question is "2022年晨光文具的现金流量表中的经营活动现金流量净额是多少？", you need to add the date filter in the WHERE clause: WHERE report_date BETWEEN '2022-01-01' AND '2022-12-31'
14) A example: If the question is "2022年建设银行的筹资活动现金流入小计是多少？", you need to return the sum value of the corresponding column at 2022: SELECT SUM(sub_total_of_ci_from_fa) FROM cash_flow_CN_STOCK_A JOIN basic_info_CN_STOCK_A ON cash_flow_CN_STOCK_A.instrument = basic_info_CN_STOCK_A.instrument WHERE date BETWEEN '2022-01-01' AND '2022-12-31' AND basic_info_CN_STOCK_A.company_name = '建设银行股份有限公司';
15) If the question is asking for a comparison between two companies, please make sure to compare or order the corresponding value and return target company_name. For example, if the question is "2022年建设银行和晨光文具哪家公司的支付其他与经营活动有关的现金更多？", you need to return the company_name: SELECT T2.company_name FROM cash_flow_CN_STOCK_A AS T1 INNER JOIN basic_info_CN_STOCK_A AS T2 ON T1.instrument = T2.instrument WHERE (T2.company_name = '建设银行股份有限公司' OR T2.company_name = '上海晨光文具股份有限公司') AND YEAR(T1.report_date) = 2022 ORDER BY T1.other_cash_paid_related_to_oa DESC LIMIT 1;
16) If a question asks what a numeric value is, there may be one or more matching rows in the database, return the sum of the values corresponding to those rows. If you don't know how many rows will match, you can return the sum of all the values. For example, if the question is "2022年东方证券的偿还债务支付的现金是多少？", you need to return the sum value of the corresponding column at 2022: SELECT SUM(cash_pay_for_debt) FROM cash_flow_CN_STOCK_A AS T1 INNER JOIN basic_info_CN_STOCK_A AS T2 ON T1.instrument = T2.instrument WHERE YEAR(T1.report_date) = 2022 AND T2.company_name = '东方证券股份有限公司';

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
7) Please only select the necessary tables and columns in the SQL query. For example, if the question is "哪家公司最早成立", you only need to select the company_name column. If the question is "比亚迪是在什么时候在主板上市的", you need to select the list_date column.
8) If the question is asking for a value or statistic of the value, please return the sum or difference according to the question. For example, if the question is "2022年晨光文具的筹资活动现金流出小计是多少？", you need to return the sum of the corresponding column: SELECT SUM(sub_total_of_cos_from_fa) FROM cash_flow_CN_STOCK_A"
9) If the question is asking for a value at a specific year, please use the date column to filter the data. For example, if the question is "2022年晨光文具的现金流量表中的经营活动现金流量净额是多少？", you need to add the date filter in the WHERE clause: WHERE report_date BETWEEN '2022-01-01' AND '2022-12-31'
10) A example: If the question is "2022年建设银行的筹资活动现金流入小计是多少？", you need to return the sum value of the corresponding column at 2022: SELECT SUM(sub_total_of_ci_from_fa) FROM cash_flow_CN_STOCK_A JOIN basic_info_CN_STOCK_A ON cash_flow_CN_STOCK_A.instrument = basic_info_CN_STOCK_A.instrument WHERE date BETWEEN '2022-01-01' AND '2022-12-31' AND basic_info_CN_STOCK_A.company_name = '建设银行股份有限公司';
11) If the question is asking for a comparison between two companies, please make sure to compare or order the corresponding value and return target company_name. For example, if the question is "2022年建设银行和晨光文具哪家公司的支付其他与经营活动有关的现金更多？", you need to return the company_name: SELECT T2.company_name FROM cash_flow_CN_STOCK_A AS T1 INNER JOIN basic_info_CN_STOCK_A AS T2 ON T1.instrument = T2.instrument WHERE (T2.company_name = '建设银行股份有限公司' OR T2.company_name = '上海晨光文具股份有限公司') AND YEAR(T1.report_date) = 2022 ORDER BY T1.other_cash_paid_related_to_oa DESC LIMIT 1;
12) If a question asks what a numeric value is, there may be one or more matching rows in the database, return the sum of the values corresponding to those rows. If you don't know how many rows will match, you can return the sum of all the values. For example, if the question is "2022年东方证券的偿还债务支付的现金是多少？", you need to return the sum value of the corresponding column at 2022: SELECT SUM(cash_pay_for_debt) FROM cash_flow_CN_STOCK_A AS T1 INNER JOIN basic_info_CN_STOCK_A AS T2 ON T1.instrument = T2.instrument WHERE YEAR(T1.report_date) = 2022 AND T2.company_name = '东方证券股份有限公司';

【Fixed SQL Query】
"""

field_extractor_template = """
Extract the main target field name from the given questions.

/* Some example questions and extracted target fields */
Question: 2022年建设银行的现金等价物的期末余额是多少？
Target fields: [现金等价物的期末余额, 公司名称, 报告日期]

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
