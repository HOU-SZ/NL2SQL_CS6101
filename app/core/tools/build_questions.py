import re
import numpy as np
# from core.utils import get_create_table_sqls
from string_tools import convert_dict_to_string


def get_create_table_sqls(tables, table_info):
    create_table_sqls = []
    for table in tables:
        cur_table_info = table_info[table]
        cur_create_table_sql = cur_table_info.split("/*")[0]
        cur_create_table_sql = cur_create_table_sql.replace("\n\n", "\n")
        if cur_create_table_sql[0] == "\n":
            cur_create_table_sql = cur_create_table_sql[1:]
        create_table_sqls.append(cur_create_table_sql)
    print("create_table_sqls: ", create_table_sqls)
    return create_table_sqls


def build_questions(tables, table_info, table_column_values_dict):
    sql_commands = get_create_table_sqls(tables, table_info)
    final_sql_commands_str = ""
    selected_dict = {}
    for i, sql_command in enumerate(sql_commands):
        sql_command, columns_to_keep = select_random_rows_from_create_table(
            sql_command)
        final_sql_commands_str += sql_command + "\n"
        table_name = tables[i]
        example_values = build_example_values(
            table_name, columns_to_keep, table_column_values_dict)
        selected_dict = {**selected_dict, **example_values}
    final_example_values_str = convert_dict_to_string(selected_dict)
    return final_sql_commands_str, final_example_values_str


def build_example_values(table_name, columns_to_keep, table_column_values_dict):
    example_values = {}
    for column in columns_to_keep:
        column_name = f"{table_name}.{column}"
        if column_name in table_column_values_dict:
            example_values[column_name] = table_column_values_dict[column_name]
    return example_values


def select_random_rows_from_create_table(sql_command):
    sql_command.replace("\t", "")
    sql_command.strip()
    if "`" in sql_command:
        sql_command = sql_command.replace("`", "")
    columns_to_keep = set()
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
    print("columns_to_keep: ", columns_to_keep)
    lines = sql_command.split("\n")
    print("len(lines): ", len(lines))
    if len(lines) <= 15:
        for line in lines[1:]:
            column_name_match = re.search(r'"(\w+)"', line)
            if not column_name_match:
                column_name_match = re.search(r'(\w+)\s', line)
            if column_name_match:
                columns_to_keep.add(column_name_match.group(1))
        return sql_command, columns_to_keep
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
        elif column_name_match:
            keep = bool(np.random.binomial(1, 0.05))
            if keep:
                new_lines.append(line)
                columns_to_keep.add(column_name_match.group(1))
    print("columns_to_keep: ", columns_to_keep)
    return "\n".join(new_lines), columns_to_keep


if __name__ == "__main__":
    tables = ['balance_sheet_CN_STOCK_A', 'basic_info_CN_STOCK_A',
              'cash_flow_CN_STOCK_A', 'income_CN_STOCK_A']
    table_info = {"balance_sheet_CN_STOCK_A": """CREATE TABLE `balance_sheet_CN_STOCK_A` (
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
/*
3 rows from balance_sheet_CN_STOCK_A table:
date	instrument	report_date	change_type	fs_quarter_index	account_receivable	accounts_payable	act_underwriting_sec	acting_td_sec	actual_received_capital	advance_payment	appropriative_reserve	asset_diff_sri	asset_diff_tbi	bill_and_account_payable	bill_and_account_receivable	bill_payable	bill_receivable	bond_payable	borrowing_funds	bs_other_compre_income	buy_resale_fnncl_assets	capital_reserve	charge_and_commi_payable	construction_in_process	construction_in_process_sum	contract_asset	contract_liab	currency_fund	debt_right_invest	derivative_fnncl_assets	derivative_fnncl_liab	dev_expenditure	differed_income_current_liab	differed_incomencl	divided_into_asset_for_sale	divided_into_liab_for_sale	dividend_payable	dividend_receivable	dt_assets	dt_liab	earned_surplus	equity_right_diff_tbi	estimated_liab	fa_calc_by_amortized_cost	fixed_asset	fixed_asset_sum	fixed_assets_disposal	flow_assets_diff_sri	flow_assets_diff_tbi	flow_debt_diff_sri	flow_debt_diff_tbi	fnncl_assets_sold_for_repur	frgn_currency_convert_diff	general_risk_provision	goodwill	held_to_maturity_invest	holder_equity_diff_sri	insurance_contract_reserve	intangible_assets	interest_payable	interest_receivable	inventory	invest_property	lease_libilities	lending_fund	liab_and_equity_diff_sri	liab_and_equity_diff_tbi	liab_diff_sri	liab_diff_tbi	loan_from_central_bank	loans_and_payments	It_deferred_expense	It_equity_invest	It_loan	It_payable	It_payable_sum	It_receivable	It_staff_salary_payable	minority_equity	noncurrent_asset_due_within1y	noncurrent_assets_diff_sri	noncurrent_assets_diff_tbi	noncurrent_liab_diff_sbi	noncurrent_liab_diff_sri	noncurrent_liab_due_in1y	oil_and_gas_asset	other_compre_fa_by_fv	other_cunrren_assets	other_current_liab	other_debt_right_invest	other_ei_invest	other_equity_instruments	other_payables	other_payables_sum	other_receivables	other_receivables_sum	other_uncurrent_fa	othr_noncurrent_assets	othr_noncurrent_liab	payroll_payable	perpetual_capital_sec	preferred_shares	preferred	premium_receivable	prepays	productive_biological_assets	project_goods_and_material	receivable_financing	rein_account_receivable	rein_contract_reserve	rein_payable	right_of_use_assets	saleable_finacial_assets	saving_and_interbank_deposit	settle_reserves	special_payable	st_bond_payable	st_borrow	tax_payable	total_assets	total_current_assets	total_current_liab	total_equity_atoopc	total_liab_and_owner_equity	total_liab	total_noncurrent_assets	total_noncurrent_liab	total_owner_equity	tradable_fnncl_assets	tradable_fnncl_liab	treasury_stock	undstrbtd_profit
2020-06-01	002986.SZA	2020-03-31	0	1	38751820.1599999964	40192764.2599999979	None	None	85000000.0000000000	55602054.5000000000	41008.8600000000	None	None	40192764.2599999979	38849820.1599999964	None	98000.0000000000	None	None	None	None	131622833.8799999952	None	None	199051890.4799999893	None	None	336463857.4200000167	None	None	None	None	None	14641535.4399999995	None	None	None	None	238529.6200000000	None	46700094.4600000009	None	None	None	None	321768063.3600000143	None	None	None	None	None	None	None	None	None	None	None	None	75680020.9699999988	None	None	82906936.5300000012	None	None	None	0E-10	0E-10	None	None	None	None	None	None	None	None	None	None	None	82500000.0000000000	None	None	None	None	None	None	None	None	None	None	None	None	None	None	6373260.2599999998	None	1198155.7000000000	None	None	None	12962158.5299999993	None	None	None	None	284380461.5099999905	None	None	None	None	None	None	None	None	None	None	None	None	None	-8359396.1699999999	1345800666.7899000645	746799231.3200000525	106770841.3799999952	1012298131.1900000572	1345800666.7899999619	251002535.5999999940	599001435.4700000286	144231694.2199999988	1094798131.1900000572	3000000.0000000000	None	None	748934193.9900000095
2020-06-01	300824.SZA	2020-03-31	1	1	None	None	None	None	None	None	None	None	None	0E-10	0E-10	None	None	None	None	None	None	None	None	None	0E-10	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	0E-10	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	0E-10	0E-10	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	0E-10	None	0E-10	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	423982600.0000000000	None	None	343674900.0000000000	423982600.0000000000	80307700.0000000000	None	None	343674900.0000000000	None	None	None	None
2020-06-01	300842.SZA	2020-03-31	0	1	279527991.1499999762	182459587.9699999988	None	None	75000000.0000000000	1381497.4500000000	None	None	None	182459587.9699999988	594215373.7899999619	None	314687382.6399999857	None	None	None	None	196992151.5300000012	None	None	0E-10	None	None	140230188.1899999976	None	None	None	None	None	None	None	None	None	None	4246165.8099999996	None	13008471.7599999998	None	None	None	None	32226073.3000000007	None	None	None	None	None	None	None	None	None	None	None	None	10750316.1799999997	None	None	190739032.7500000000	None	None	None	0E-10	0E-10	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	1013059.7600000000	None	130617.7000000000	None	None	None	2428595.7200000002	None	None	None	None	56018735.3599999994	None	None	None	None	None	None	None	None	None	None	None	None	405395395.2599999905	9898203.6600000001	1040698192.7400000095	993475637.4500000477	602576339.8200000525	438121852.9200000167	1040698192.7400000095	602576339.8200000525	47222555.2899999991	None	438121852.9200000167	12141689.6600000001	None	None	153121229.6299999952
*/""",
                  "basic_info_CN_STOCK_A": """CREATE TABLE `basic_info_CN_STOCK_A` (
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
/*
3 rows from basic_info_CN_STOCK_A table:
instrument	delist_date	company_type	company_name	company_province	list_board	company_found_date	name	list_date
000001.SZA	None	公众企业	平安银行股份有限公司	广东省	主板	1987-12-22 00:00:00	平安银行	1991-04-03
000002.SZA	None	公众企业	万科企业股份有限公司	广东省	主板	1984-05-30 00:00:00	万科A	1991-01-29
000003.SZA	2002-06-14	民营企业	金田实业(集团)股份有限公司	广东省	主板	1988-03-10 00:00:00	PT金田A(退市)	1991-07-03
*/""",
                  "cash_flow_CN_STOCK_A": """CREATE TABLE `cash_flow_CN_STOCK_A`
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
/*
3 rows from cash_flow_CN_STOCK_A table:
date	instrument	report_date	change_type	fs_quarter_index	asset_impairment_reserve	borrowing_net_add_central_bank	borrowing_net_increase_amt	cash_of_orig_ic_indemnity	cash_paid_for_assets	cash_paid_for_interests_etc	cash_paid_for_pd	cash_paid_of_distribution	cash_paid_to_staff_etc	cash_pay_for_debt	cash_received_from_bond_issue	cash_received_from_orig_ic	cash_received_of_absorb_invest	cash_received_of_borrowing	cash_received_of_dspsl_invest	cash_received_of_interest_etc	cash_received_of_other_fa	cash_received_of_other_oa	cash_received_of_othr_fa	cash_received_of_sales_service	cb_due_within1y	cce_net_add_amt_diff_sri_dm	cce_net_add_amt_diff_tbi_dm	cce_net_add_diff_im_sri	cce_net_add_diff_im_tbi	cr_from_minority_holders	credit_impairment_loss	dap_paid_to_minority_holder	debt_tranfer_to_capital	deposit_and_interbank_net_add	depreciation_etc	dt_assets_decrease	dt_liab_increase	effect_of_exchange_chg_on_cce	ending_balance_of_cash	fa_cash_in_flow_diff_sri	fa_cash_in_flow_diff_tbi	fa_cash_out_flow_diff_sri	fa_cash_out_flow_diff_tbi	final_balance_of_cce	finance_cost_cfs	finance_lease_fixed_assets	fixed_assets_scrap_loss	goods_buy_and_service_cash_pay	ia_cash_inflow_diff_sri	ia_cash_inflow_diff_tbi	ia_cash_outflow_diff_sri	ia_cash_outflow_diff_tbi	increase_of_operating_item	initial_balance_of_cash	initial_balance_of_cce	initial_cce_balance	intangible_assets_amortized	inventory_decrease	invest_income_cash_received	invest_loss	invest_paid_cash	lending_net_add_other_org	loan_and_advancenet_add	loss_from_fv_chg	loss_of_disposal_assets	It_deferred_expenses_amrtzt	naa_of_cb_and_interbank	naa_of_disposal_fnncl_assets	naaassured_saving_and_invest	ncf_diff_from_fa_sri	ncf_diff_from_fa_tbi	ncf_diff_from_ia_sri	ncf_diff_from_ia_tbi	ncf_diff_from_oa_im_sri	ncf_diff_from_oa_im_tbi	ncf_diff_of_oa_sri	ncf_diff_of_oa_tbi	ncf_from_fa	ncf_from_ia	ncf_from_oa_im	ncf_from_oa	net_add_in_pledge_loans	net_add_in_repur_capital	net_cash_amt_from_branch	net_cash_of_disposal_assets	net_cash_of_disposal_branch	net_cash_received_from_rein	net_increase_in_cce_im	net_increase_in_cce	np_cfs	oa_cash_inflow_diff_sri	oa_cash_inflow_diff_tbi	oa_cash_outflow_diff_sri	oa_cash_outflow_diff_tbi	operating_items_decrease	other_cash_paid_related_to_ia	other_cash_paid_related_to_oa	othrcash_paid_relating_to_fa	payments_of_all_taxes	refund_of_tax_and_levies	si_final_balance_of_cce	si_other	sub_total_of_ci_from_fa	sub_total_of_ci_from_ia	sub_total_of_ci_from_oa	sub_total_of_cos_from_fa	sub_total_of_cos_from_ia	sub_total_of_cos_from_oa
2021-06-01	001207.SZA	2021-03-31	0	4	None	None	None	None	10181123.6300000008	None	None	1459820.4099999999	19302293.2899999991	None	None	None	None	None	275038853.4599999785	None	None	5664507.9299999997	None	190139593.4499999881	None	None	None	None	None	None	4222312.5499999998	None	None	None	None	None	None	41163.6600000000	None	None	None	None	None	29451747.8599999994	None	None	None	174371121.3100000024	None	None	None	None	None	None	None	71074349.3100000024	None	None	176566.3500000000	None	287048297.0000000000	None	None	None	None	None	None	None	None	None	0E-10	None	0E-10	None	None	None	0E-10	-1459820.4099999999	-22014000.8200000003	None	-18189943.8799999990	None	None	None	None	None	None	None	-41622601.4500000030	None	None	None	None	None	None	None	11533272.3900000006	None	13205598.1600000001	4418239.8899999997	None	None	None	275215419.8100000024	200222341.2700000107	1459820.4099999999	297229420.6299999952	218412285.1500000060
2021-06-01	301022.SZA	2021-03-31	1	4	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	-6690500.0000000000	None	-4922100.0000000000	None	None	None	13552600.0000000000	-6690500.0000000000	-4922100.0000000000	None	13552600.0000000000	None	None	None	None	None	None	None	631100.0000000000	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None
2021-06-01	301023.SZA	2021-03-31	1	4	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	30385500.0000000000	None	None	None	8245500.0000000000	None	30385500.0000000000	None	8245500.0000000000	None	None	None	None	None	None	None	39204000.0000000000	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None
*/""",
                  "income_CN_STOCK_A": """CREATE TABLE `income_CN_STOCK_A`
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
/*
3 rows from income_CN_STOCK_A table:
date	instrument	report_date	change_type	fs_quarter_index	amortized_cost_fnncl_ass_cfrm	asset_change_due_to_remeasure	asset_disposal_gain	asset_impairment_loss	basic_eps	cannt_reclass_gal_equity_law	cannt_reclass_to_gal	cash_flow_hedge_reserve	cf_hedging_gal_valid_part	charge_and_commi_expenses	commi_on_insurance_policy	compensate_net_pay	continued_operating_np	corp_credit_risk_fvc	credit_impairment_loss	dlt_earnings_per_share	earned_premium	exchange_gain	extract_ic_reserve_net_amt	fa_reclassi_amt	fc_convert_diff	fc_interest_income	fee_and_commi_income	financing_expenses	fv_chg_income	ii_from_jc_etc	income_tax_cost	interest_fee	interest_income	interest_payout	invest_income	manage_fee	minority_gal	net_open_hedge_income	non_operating_income	noncurrent_asset_dispose_gain	noncurrent_asset_dispose_loss	nonoperating_cost	np_atoopc	np_diff_sri	np_diff_tbi	op_diff_sri	op_diff_tbi	operating_cost_diff_sri	operating_cost_diff_tbi	operating_cost	operating_revenue_diff_sri	operating_revenue_diff_tbi	operating_taxes_and_surcharge	operating_total_cost	operating_total_revenue	other_compre_income	other_debt_right_invest_fvc	other_debt_right_invest_ir	other_equity_invest_fvc	other_income	other_not_reclass_to_gal	other_reclass_to_gal	othrcompre_income_atms	othrcompre_income_atoopc	rad_cost_sum	reclass_and_salable_gal	reclass_to_gal	reclass_togal_in_equity_law	refunded_premium	rein_expenditure	revenue	saleable_fv_chg_gal	sales_fee	stop_operating_np	total_compre_income_atsopc	total_compre_income	total_profit_diff_sri	total_profit_diff_tbi	total_profit
2020-06-01	002986.SZA	2020-03-31	0	1	None	None	None	None	0.3200000000	None	None	None	None	None	None	None	27147565.3399999999	None	None	0.3200000000	None	None	None	None	None	-208159.5400000000	None	-616915.6300000000	None	None	953703.1400000000	None	None	None	244535.1100000000	4581845.3799999999	None	None	481074.1000000000	None	None	298543.0200000000	27147565.3399999999	None	None	None	None	None	None	547983896.0800000429	None	None	404801.2800000000	575306136.9500000477	598151678.9199999571	None	None	None	None	4828660.3200000003	None	None	None	None	18352213.1900000013	None	None	None	None	None	598151678.9199999571	None	4600296.6500000004	None	27147565.3399999999	27147565.3399999999	None	None	28101268.4800000004
2020-06-01	300824.SZA	2020-03-31	1	1	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	21597600.0000000000	None	None	None	None	None	None	None	None	None	None	None	113799400.0000000000	None	None	None	None	None	None	None	None	None	None	None	None	None	None	None	113799400.0000000000	None	None	None	None	None	None	None	25203200.0000000000
2020-06-01	300842.SZA	2020-03-31	0	1	None	None	None	460670.9300000000	0.4700000000	None	None	None	None	None	None	None	35242183.6199999973	None	1051848.5600000001	0.4700000000	None	None	None	None	None	77135.4600000000	None	5172065.2000000002	5462081.0000000000	None	4956410.0899999999	1313073.0500000000	None	None	14577343.5600000005	1950718.2900000000	None	None	1859585.4600000000	None	None	196330.6400000000	35242183.6199999973	None	None	None	None	None	None	184804911.0000000000	None	None	561606.7700000000	201912188.0999999940	220408102.4300000072	None	None	None	None	None	None	None	None	None	5084043.2699999996	None	None	None	None	None	220408102.4300000072	None	2826324.0800000001	None	35242183.6199999973	35242183.6199999973	None	None	40198593.7100000009
*/"""
                  }
    table_column_values_dict = {
        'basic_info_CN_STOCK_A.instrument': ['002089.SZA', '002543.SZA', '300081.SZ', '688056.SHA', '603887.SHA', '830946.BJA', '832786.BJA', '000787.SZA'],
        'basic_info_CN_STOCK_A.company_name': ["珠海格力电器股份有限公司", "比亚迪股份有限公司", "平安银行股份有限公司", "华夏银行股份有限公司", "中国平安股份有限公司", "四川长虹新能源科技股份有限公司", "同享(苏州)电子材料科技股份有限公司", "东华能源股份有限公司", "同兴环保科技股份有限公司"],
        'basic_info_CN_STOCK_A.name': ['平安银行', '格力电器', '比亚迪', '长虹能源', '华夏银行', '中国平安', '同享科技', '东华能源', '同兴环保'],
        'balance_sheet_CN_STOCK_A.report_date': ['2020-03-31', '2022-03-31', '2021-06-30', '2022-06-30', '2022-03-31', '2022-06-30', '2022-09-30', '2022-12-31']
    }

    print(build_questions(tables, table_info, table_column_values_dict))
