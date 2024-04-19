-- # Table: account
-- [
--   (account_id, the id of the account. Value examples: [11382, 11362, 2, 1, 2367].),
--   (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].),
--   (frequency, frequency of the acount. Value examples: ['POPLATEK MESICNE', 'POPLATEK TYDNE', 'POPLATEK PO OBRATU'].),
--   (date, the creation date of the account. Value examples: ['1997-12-29', '1997-12-28'].)
-- ]
CREATE TABLE account (
    account_id INT PRIMARY KEY,
    -- the id of the account
    district_id INT,
    -- location of branch
    frequency VARCHAR(50),
    -- frequency of the acount
    date DATE -- the creation date of the account
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);
INSERT INTO account
VALUES (11382, 77, 'POPLATEK MESICNE', '1997-12-29');
INSERT INTO account
VALUES (11362, 76, 'POPLATEK TYDNE', '1997-12-28');
INSERT INTO account
VALUES (2, 2, 'POPLATEK PO OBRATU', '1993-02-26');
-- # Table: client
-- [
--   (client_id, the unique number. Value examples: [13998, 13971, 2, 1, 2839].),
--   (gender, gender. Value examples: ['M', 'F']. And F：female . M：male ),
--   (birth_date, birth date. Value examples: ['1987-09-27', '1986-08-13'].),
--   (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].)
-- ]
CREATE TABLE client (
    client_id INT PRIMARY KEY,
    -- the unique number
    gender CHAR(1),
    -- gender. F：female . M：male
    birth_date DATE,
    -- birth date
    district_id INT -- location of branch
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);
INSERT INTO client
VALUES (13998, 'M', '1987-09-27', 77);
INSERT INTO client
VALUES (13971, 'F', '1986-08-13', 76);
INSERT INTO client
VALUES (2, 'M', '1972-02-26', 2);
-- # Table: loan
-- [
--   (loan_id, the id number identifying the loan data. Value examples: [4959, 4960, 4961].),
--   (account_id, the id number identifying the account. Value examples: [10, 80, 55, 43].),
--   (date, the date when the loan is approved. Value examples: ['1998-07-12', '1998-04-19'].),
--   (amount, the amount of the loan. Value examples: [1567, 7877, 9988].),
--   (duration, the duration the loan. Value examples: [60, 48, 24, 12, 36].),
--   (payments, the payments the loan. Value examples: [3456, 8972, 9845].),
--   (status, the status of the loan. Value examples: ['C', 'A', 'D', 'B'].)
-- ]
CREATE TABLE loan (
    loan_id INT PRIMARY KEY,
    -- the id number identifying the loan data
    account_id INT,
    -- the id number identifying the account
    date DATE,
    -- the date when the loan is approved
    amount INT,
    -- the amount of the loan
    duration INT,
    -- the duration the loan
    payments INT,
    -- the payments the loan
    status CHAR(1) -- the status of the loan
    FOREIGN KEY (account_id) REFERENCES account(account_id)
);
INSERT INTO loan
VALUES (4959, 10, '1998-07-12', 1567, 60, 3456, 'C');
INSERT INTO loan
VALUES (4960, 80, '1998-04-19', 7877, 48, 8972, 'A');
INSERT INTO loan
VALUES (4961, 55, '1998-07-05', 9988, 24, 9845, 'D');
-- # Table: district
-- [
--   (district_id, location of branch. Value examples: [77, 76].),
--   (A2, area in square kilometers. Value examples: [50.5, 48.9].),
--   (A4, number of inhabitants. Value examples: [95907, 95616].),
--   (A5, number of households. Value examples: [35678, 34892].),
--   (A6, literacy rate. Value examples: [95.6, 92.3, 89.7].),
--   (A7, number of entrepreneurs. Value examples: [1234, 1456].),
--   (A8, number of cities. Value examples: [5, 4].),
--   (A9, number of schools. Value examples: [15, 12, 10].),
--   (A10, number of hospitals. Value examples: [8, 6, 4].),
--   (A11, average salary. Value examples: [12541, 11277].),
--   (A12, poverty rate. Value examples: [12.4, 9.8].),
--   (A13, unemployment rate. Value examples: [8.2, 7.9].),
--   (A15, number of crimes. Value examples: [256, 189].)
-- ]
CREATE TABLE district (
    district_id INT PRIMARY KEY,
    -- location of branch
    A2 FLOAT,
    -- area in square kilometers
    A4 INT,
    -- number of inhabitants
    A5 INT,
    -- number of households
    A6 FLOAT,
    -- literacy rate
    A7 INT,
    -- number of entrepreneurs
    A8 INT,
    -- number of cities
    A9 INT,
    -- number of schools
    A10 INT,
    -- number of hospitals
    A11 INT,
    -- average salary
    A12 FLOAT,
    -- poverty rate
    A13 FLOAT,
    -- unemployment rate
    A15 INT -- number of crimes
);
INSERT INTO district
VALUES (
        77,
        50.5,
        95907,
        35678,
        95.6,
        1234,
        5,
        15,
        8,
        12541,
        12.4,
        8.2,
        256
    );
INSERT INTO district
VALUES (
        76,
        48.9,
        95616,
        34892,
        92.3,
        1456,
        4,
        12,
        6,
        11277,
        9.8,
        7.9,
        189
    );
INSERT INTO district
VALUES (
        2,
        50.5,
        95907,
        35678,
        95.6,
        1234,
        5,
        15,
        8,
        12541,
        12.4,
        8.2,
        256
    );
-- # Table: frpm
-- [
--   (CDSCode, CDSCode. Value examples: ['01100170109835', '01100170112607'].),
--   (Charter School (Y/N), Charter School (Y/N). Value examples: [1, 0, None]. And 0: N;. 1: Y),
--   (Enrollment (Ages 5-17), Enrollment (Ages 5-17). Value examples: [5271.0, 4734.0].),
--   (Free Meal Count (Ages 5-17), Free Meal Count (Ages 5-17). Value examples: [3864.0, 2637.0]. And eligible free rate = Free Meal Count / Enrollment)
-- ]
CREATE TABLE frpm (
    CDSCode VARCHAR(50) PRIMARY KEY,
    -- CDSCode
    Charter School (Y / N),
    -- 0: N;. 1: Y
    Enrollment (Ages 5 -17) FLOAT,
    -- Enrollment (Ages 5-17)
    Free Meal Count (Ages 5 -17) FLOAT -- Free Meal Count (Ages 5-17)
    FOREIGN KEY (CDSCode) REFERENCES satscores(cds)
);
INSERT INTO frpm
VALUES ('01100170109835', 1, 5271.0, 3864.0);
INSERT INTO frpm
VALUES ('01100170112607', 0, 4734.0, 2637.0);
INSERT INTO frpm
VALUES ('01100170109835', 1, 5271.0, 3864.0);
-- # Table: satscores
-- [
--   (cds, California Department Schools. Value examples: ['10101080000000', '10101080109991'].),
--   (sname, school name. Value examples: ['None', 'Middle College High', 'John F. Kennedy High', 'Independence High', 'Foothill High'].),
--   (NumTstTakr, Number of Test Takers in this school. Value examples: [24305, 4942, 1, 0, 280]. And number of test takers in each school),
--   (AvgScrMath, average scores in Math. Value examples: [699, 698, 289, None, 492]. And average scores in Math),
--   (NumGE1500, Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500. Value examples: [5837, 2125, 0, None, 191]. And Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500. . commonsense evidence:. . Excellence Rate = NumGE1500 / NumTstTakr)
-- ]
CREATE TABLE satscores (
    cds VARCHAR(50) PRIMARY KEY,
    -- California Department Schools
    sname VARCHAR(50),
    -- school name
    NumTstTakr INT,
    -- number of test takers in each school
    AvgScrMath INT,
    -- average scores in Math
    NumGE1500 INT -- Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500
);
INSERT INTO satscores
VALUES ('10101080000000', 'None', 24305, 699, 5837);
INSERT INTO satscores
VALUES (
        '10101080109991',
        'Middle College High',
        4942,
        698,
        2125
    );
INSERT INTO satscores
VALUES (
        '10101080009988',
        'John F. Kennedy High',
        2233,
        500,
        3311
    );