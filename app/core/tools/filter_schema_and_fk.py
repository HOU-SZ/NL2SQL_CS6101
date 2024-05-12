import re


def apply_dictionary(sql_commands, foreign_keys, dictionary):
    modified_sql_commands = {}
    droped_tables = []
    droped_table_columns = {}

    # TODO优化：每张表至少保留主键外键信息
    for sql_command in sql_commands:
        sql_command.replace("\t", "")
        sql_command.strip()
        if "`" in sql_command:
            sql_command = sql_command.replace("`", "")
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
                    # Keep primary key columns
                    if "PRIMARY KEY" in sql_command:
                        primary_key = re.search(
                            r'PRIMARY KEY \((.*?)\)', sql_command)
                        if primary_key is not None:
                            primary_key = primary_key.group(1)
                        if primary_key is None:
                            primary_key = re.search(
                                r'PRIMARY KEY\((.*?)\)', sql_command)
                            if primary_key is not None:
                                primary_key = primary_key.group(1)
                        primary_key_columns = set(
                            re.findall(r'"(.*?)"', primary_key))
                        if len(primary_key_columns) == 0:
                            primary_key_columns = set(
                                re.findall(r'(\w+)', primary_key))
                        columns_to_keep = columns_to_keep.union(
                            primary_key_columns)
                    # Keep foreign key columns
                    if "FOREIGN KEY" in sql_command:
                        foreign_key = re.search(
                            r'FOREIGN KEY \((.*?)\) REFERENCES', sql_command)
                        if foreign_key is not None:
                            foreign_key = foreign_key.group(1)
                        if foreign_key is None:
                            foreign_key = re.search(
                                r'FOREIGN KEY\((.*?)\) REFERENCES', sql_command)
                            if foreign_key is not None:
                                foreign_key = foreign_key.group(1)
                        foreign_key_columns = set(
                            re.findall(r'"(.*?)"', foreign_key))
                        if len(foreign_key_columns) == 0:
                            foreign_key_columns = set(
                                re.findall(r'(\w+)', foreign_key))
                        columns_to_keep = columns_to_keep.union(
                            foreign_key_columns)
                    lines = sql_command.split("\n")
                    new_lines = [lines[0]]  # Keep the CREATE TABLE line
                    for line in lines[1:]:
                        column_name_match = re.search(r'"(\w+)"', line)
                        if not column_name_match:
                            column_name_match = re.search(r'(\w+)\s', line)
                        # if the line is the last line of the create table command
                        if len(line.strip()) > 0 and line.strip()[0] == ")":
                            new_lines.append(line)
                            new_lines.append("\n")
                        elif "PRIMARY KEY" in line:
                            new_lines.append(line)
                        elif "FOREIGN KEY" in line:
                            new_lines.append(line)
                        elif column_name_match and column_name_match.group(1) in columns_to_keep:
                            new_lines.append(line)
                        elif column_name_match and column_name_match.group(1) not in columns_to_keep:
                            if table_name not in droped_table_columns:
                                droped_table_columns[table_name] = []
                            droped_table_columns[table_name].append(
                                column_name_match.group(1))
                    modified_sql_commands[table_name] = "\n".join(
                        new_lines)
            else:
                continue
                # modified_sql_commands[table_name] = sql_command
    # # Remove foreign keys constraints referencing dropped tables (right of the "=" sign)
    # for table in droped_tables:
    #     for table_name, fks in foreign_keys.items():
    #         for fk in fks:
    #             right_table = fk.split("=")[1].split(".")[0]
    #             if right_table == table:
    #                 fks.remove(fk)
    #         # remove the command line form the corresponding create table command
    #         for table_name, sql_command in modified_sql_commands.items():
    #             if table_name == table:
    #                 del modified_sql_commands[table_name]
    #             elif "REFERENCES " + table in sql_command:
    #                 modified_sql_commands[table_name] = re.sub(
    #                     r'FOREIGN KEY\("(.*?)"\) REFERENCES ' + table + ' \("(.*?)"\)', '', sql_command)
    #                 modified_sql_commands[table_name] = re.sub(
    #                     r'\n\s*\n', '\n', modified_sql_commands[table_name])
    #                 modified_sql_commands[table_name] = re.sub(
    #                     r',\s*,', ',', modified_sql_commands[table_name])

    # # Remove foreign keys constraints referencing columns that are not kept (left of the "=" sign)
    # for table_name, fks in foreign_keys.items():
    #     for fk in fks:
    #         left_table = fk.split("=")[0].split(".")[0]
    #         left_column = fk.split("=")[0].split(".")[1]
    #         if left_table in dictionary and type(dictionary[left_table]) == list and left_column not in dictionary[left_table]:
    #             fks.remove(fk)

    # # Remove foreign keys constraints referencing columns that are not kept (right of the "=" sign)
    # for table_name, fks in foreign_keys.items():
    #     for fk in fks:
    #         right_table = fk.split("=")[1].split(".")[0]
    #         right_column = fk.split("=")[1].split(".")[1]
    #         if right_table in dictionary and type(dictionary[right_table]) == list and right_column not in dictionary[right_table]:
    #             fks.remove(fk)

    # # Remove all unnecessary REFERENCES in the modified_sql_commands
    # for table_name, droped_columns in droped_table_columns.items():
    #     for column in droped_columns:
    #         for table_name, sql_command in modified_sql_commands.items():
    #             match_str_1 = "REFERENCES " + \
    #                 table_name + '("' + column + '")'
    #             match_str_2 = "REFERENCES " + \
    #                 table_name + ' ("' + column + '")'
    #             if match_str_1 in sql_command:
    #                 sql_command = sql_command.replace(match_str_1, '')
    #             elif match_str_2 in sql_command:
    #                 sql_command = sql_command.replace(match_str_2, '')
    #             modified_sql_commands[table_name] = sql_command
    #             modified_sql_commands[table_name] = re.sub(
    #                 r'\n\s*\n', '\n', modified_sql_commands[table_name])
    #             modified_sql_commands[table_name] = re.sub(
    #                 r',\s*,', ',', modified_sql_commands[table_name])
    # return modified_sql_commands.values(), foreign_keys


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

    sql_commands_2 = [
        '''CREATE TABLE `balance_sheet_CN_STOCK_A` (
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
                PRIMARY KEY ("date", "instrument", "report_date")
                FOREIGN KEY(instrument) REFERENCES basic_info_CN_STOCK_A (instrument)
            )DEFAULT CHARSET=utf8mb4 COMMENT='资产负债表' ENGINE=InnoDB COLLATE utf8mb4_unicode_ci''',
        '''CREATE TABLE basic_info_CN_STOCK_A (
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
            )COMMENT='A股股票基本信息' DEFAULT CHARSET=utf8mb3 ENGINE=InnoDB'''
    ]
    foreign_keys_2 = {}
    dictionary_2 = {
        "balance_sheet_CN_STOCK_A": ["date", "instrument", "report_date"], "basic_info_CN_STOCK_A": ["company_province"],
    }

    modified_sql_commands, foreign_keys = apply_dictionary(
        sql_commands_2, foreign_keys_2, dictionary_2)

    print("SQL create table命令：")
    for sql_command in modified_sql_commands:
        print(sql_command)

    print("\nforeign keys信息：")
    print(foreign_keys)
