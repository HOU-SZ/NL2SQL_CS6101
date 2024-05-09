import numpy
from sentence_transformers import SentenceTransformer
from thefuzz import fuzz
import time


def calculate_similarity(embedder: SentenceTransformer, text1: str, text2: str) -> float:
    # Tokenize and encode the texts
    encoding1 = embedder.encode(text1)
    encoding2 = embedder.encode(text2)

    # Calculate the cosine similarity between the embeddings
    similarity = numpy.dot(encoding1, encoding2) / \
        (numpy.linalg.norm(encoding1) * numpy.linalg.norm(encoding2))
    return similarity


def fuzzy_similarity(text1: str, text2: str) -> float:
    similarity = fuzz.ratio(text1, text2) / 100
    return similarity


def get_table_and_columns_by_similarity(embedder: SentenceTransformer, fields: list, comments_list: list) -> dict:
    """
    Get the table and columns that are most similar to the given fields.
    """
    results = []
    selected_tables_and_columns = []
    if comments_list is None or len(comments_list) == 0:
        return results, selected_tables_and_columns
    for field in fields:
        sorted_comments_list = sorted(comments_list, key=lambda x: calculate_similarity(
            embedder, list(x.keys())[0], field), reverse=True)
        selected_comments = []
        top_similarity = 0
        for i in range(len(sorted_comments_list)):
            comment = sorted_comments_list[i]
            if i == 0:
                top_similarity = calculate_similarity(
                    embedder, list(comment.keys())[0], field)
                selected_comments.append(comment)
                selected_tables_and_columns.append(list(comment.values())[0])
            elif top_similarity - calculate_similarity(embedder, list(comment.keys())[0], field) < 0.05:
                selected_comments.append(comment)
                selected_tables_and_columns.append(list(comment.values())[0])
        results.append({field: selected_comments})
    return results, selected_tables_and_columns


def get_table_and_columns_by_fuzzy_similarity(fields: list, comments_list: list) -> dict:
    """
    Get the table and columns that are most similar to the given fields.
    """
    results = []
    selected_tables_and_columns = []
    if comments_list is None or len(comments_list) == 0:
        return results, selected_tables_and_columns
    for field in fields:
        sorted_comments_list = sorted(comments_list, key=lambda x: fuzzy_similarity(
            list(x.keys())[0], field), reverse=True)
        selected_comments = []
        top_similarity = 0
        for i in range(len(sorted_comments_list)):
            comment = sorted_comments_list[i]
            if i == 0:
                top_similarity = fuzzy_similarity(
                    list(comment.keys())[0], field)
                selected_comments.append(comment)
                selected_tables_and_columns.append(list(comment.values())[0])
            elif top_similarity - fuzzy_similarity(list(comment.keys())[0], field) < 0.05:
                selected_comments.append(comment)
                selected_tables_and_columns.append(list(comment.values())[0])
        results.append({field: selected_comments})
    return results, selected_tables_and_columns


if __name__ == "__main__":
    print("start")
    # embedder = SentenceTransformer('uer/sbert-base-chinese-nli')
    # fields = ['现金等价物的期末余额', '公司名称', '报告日期', '退市日期']
    # comments_list = [{'公告日': 'balance_sheet_CN_STOCK_A.date'}, {'股票代码': 'balance_sheet_CN_STOCK_A.instrument'}, {'报告期': 'balance_sheet_CN_STOCK_A.report_date'}, {'对应季度': 'balance_sheet_CN_STOCK_A.fs_quarter_index'}, {'应收账款': 'balance_sheet_CN_STOCK_A.account_receivable'}, {'应付账款': 'balance_sheet_CN_STOCK_A.accounts_payable'}, {'代理承销证券款': 'balance_sheet_CN_STOCK_A.act_underwriting_sec'}, {'代理买卖证券款': 'balance_sheet_CN_STOCK_A.acting_td_sec'}, {'预收款项': 'balance_sheet_CN_STOCK_A.advance_payment'}, {'专项储备': 'balance_sheet_CN_STOCK_A.appropriative_reserve'}, {'应付票据及应付账款': 'balance_sheet_CN_STOCK_A.bill_and_account_payable'}, {'应收票据及应收账款': 'balance_sheet_CN_STOCK_A.bill_and_account_receivable'}, {'应付票据': 'balance_sheet_CN_STOCK_A.bill_payable'}, {'应收票据': 'balance_sheet_CN_STOCK_A.bill_receivable'}, {'应付债券': 'balance_sheet_CN_STOCK_A.bond_payable'}, {'拆入资金': 'balance_sheet_CN_STOCK_A.borrowing_funds'}, {'其他综合收益': 'balance_sheet_CN_STOCK_A.bs_other_compre_income'}, {'买入返售金融资产': 'balance_sheet_CN_STOCK_A.buy_resale_fnncl_assets'}, {'资本公积': 'balance_sheet_CN_STOCK_A.capital_reserve'}, {'应付手续费及佣金': 'balance_sheet_CN_STOCK_A.charge_and_commi_payable'}, {'在建工程': 'balance_sheet_CN_STOCK_A.construction_in_process'}, {'在建工程合计': 'balance_sheet_CN_STOCK_A.construction_in_process_sum'}, {'合同资产': 'balance_sheet_CN_STOCK_A.contract_asset'}, {'合同负债': 'balance_sheet_CN_STOCK_A.contract_liab'}, {'货币资金': 'balance_sheet_CN_STOCK_A.currency_fund'}, {'债权投资': 'balance_sheet_CN_STOCK_A.debt_right_invest'}, {'衍生金融资产': 'balance_sheet_CN_STOCK_A.derivative_fnncl_assets'}, {'衍生金融负债': 'balance_sheet_CN_STOCK_A.derivative_fnncl_liab'}, {'开发支出': 'balance_sheet_CN_STOCK_A.dev_expenditure'}, {'持有待售资产': 'balance_sheet_CN_STOCK_A.divided_into_asset_for_sale'}, {'持有待售负债': 'balance_sheet_CN_STOCK_A.divided_into_liab_for_sale'}, {'应付股利': 'balance_sheet_CN_STOCK_A.dividend_payable'}, {'应收股利': 'balance_sheet_CN_STOCK_A.dividend_receivable'}, {'递延所得税资产': 'balance_sheet_CN_STOCK_A.dt_assets'}, {'递延所得税负债': 'balance_sheet_CN_STOCK_A.dt_liab'}, {'盈余公积': 'balance_sheet_CN_STOCK_A.earned_surplus'}, {'预计负债': 'balance_sheet_CN_STOCK_A.estimated_liab'}, {'以摊余成本计量的金融资产': 'balance_sheet_CN_STOCK_A.fa_calc_by_amortized_cost'}, {'固定 资产': 'balance_sheet_CN_STOCK_A.fixed_asset'}, {'固定资产合计': 'balance_sheet_CN_STOCK_A.fixed_asset_sum'}, {'固定资产清理': 'balance_sheet_CN_STOCK_A.fixed_assets_disposal'}, {'卖出回购金融资产款': 'balance_sheet_CN_STOCK_A.fnncl_assets_sold_for_repur'}, {'外币报表折算差额': 'balance_sheet_CN_STOCK_A.frgn_currency_convert_diff'}, {'一般 风险准备': 'balance_sheet_CN_STOCK_A.general_risk_provision'}, {'商誉': 'balance_sheet_CN_STOCK_A.goodwill'}, {'持有至到期投资': 'balance_sheet_CN_STOCK_A.held_to_maturity_invest'}, {'保险合同准备金': 'balance_sheet_CN_STOCK_A.insurance_contract_reserve'}, {'无形资产': 'balance_sheet_CN_STOCK_A.intangible_assets'}, {'应付利息': 'balance_sheet_CN_STOCK_A.interest_payable'}, {'应收利息': 'balance_sheet_CN_STOCK_A.interest_receivable'}, {'存货': 'balance_sheet_CN_STOCK_A.inventory'}, {'投资性房地产': 'balance_sheet_CN_STOCK_A.invest_property'}, {'租赁负债': 'balance_sheet_CN_STOCK_A.lease_libilities'}, {'拆出资金': 'balance_sheet_CN_STOCK_A.lending_fund'}, {'向中央银行借款': 'balance_sheet_CN_STOCK_A.loan_from_central_bank'}, {'发放贷款及垫款': 'balance_sheet_CN_STOCK_A.loans_and_payments'}, {'长期待摊费用': 'balance_sheet_CN_STOCK_A.It_deferred_expense'}, {'长期股权投资': 'balance_sheet_CN_STOCK_A.It_equity_invest'}, {'长期借款': 'balance_sheet_CN_STOCK_A.It_loan'}, {'长期应付款': 'balance_sheet_CN_STOCK_A.It_payable'}, {'长期应付款合计': 'balance_sheet_CN_STOCK_A.It_payable_sum'}, {'长期应收款': 'balance_sheet_CN_STOCK_A.It_receivable'}, {'长期应付职工薪酬': 'balance_sheet_CN_STOCK_A.It_staff_salary_payable'}, {'少数股东权益': 'balance_sheet_CN_STOCK_A.minority_equity'}, {'一年内到期的非流动资产': 'balance_sheet_CN_STOCK_A.noncurrent_asset_due_within1y'}, {'一年内到期的非流动负债': 'balance_sheet_CN_STOCK_A.noncurrent_liab_due_in1y'}, {'油气资产': 'balance_sheet_CN_STOCK_A.oil_and_gas_asset'}, {'以公允价值计量且其 变动计入其他综合收益的金融资产': 'balance_sheet_CN_STOCK_A.other_compre_fa_by_fv'}, {'其他流动资产': 'balance_sheet_CN_STOCK_A.other_cunrren_assets'}, {'其他流动负债': 'balance_sheet_CN_STOCK_A.other_current_liab'}, {'其他债权投资': 'balance_sheet_CN_STOCK_A.other_debt_right_invest'}, {'其他权益工具投资': 'balance_sheet_CN_STOCK_A.other_ei_invest'}, {'其他权益工具': 'balance_sheet_CN_STOCK_A.other_equity_instruments'}, {'其他应付款': 'balance_sheet_CN_STOCK_A.other_payables'}, {'其他应付款合计': 'balance_sheet_CN_STOCK_A.other_payables_sum'}, {'其他应收款': 'balance_sheet_CN_STOCK_A.other_receivables'}, {'其他应收款合计': 'balance_sheet_CN_STOCK_A.other_receivables_sum'}, {' 其他非流动金融资产': 'balance_sheet_CN_STOCK_A.other_uncurrent_fa'}, {'其他非流动资产': 'balance_sheet_CN_STOCK_A.othr_noncurrent_assets'}, {'其他非流动负债': 'balance_sheet_CN_STOCK_A.othr_noncurrent_liab'}, {'应付职工薪酬': 'balance_sheet_CN_STOCK_A.payroll_payable'}, {'永续债': 'balance_sheet_CN_STOCK_A.perpetual_capital_sec'}, {'其中优 先股': 'balance_sheet_CN_STOCK_A.preferred_shares'}, {'优先股': 'balance_sheet_CN_STOCK_A.preferred'}, {'应收保费': 'balance_sheet_CN_STOCK_A.premium_receivable'}, {'预付 款项': 'balance_sheet_CN_STOCK_A.prepays'}, {'生产性生物资产': 'balance_sheet_CN_STOCK_A.productive_biological_assets'}, {'工程物资': 'balance_sheet_CN_STOCK_A.project_goods_and_material'}, {'应收款项融资': 'balance_sheet_CN_STOCK_A.receivable_financing'}, {'应收分保账款': 'balance_sheet_CN_STOCK_A.rein_account_receivable'}, {'应收分保合同 准备金': 'balance_sheet_CN_STOCK_A.rein_contract_reserve'}, {'应付分保账款': 'balance_sheet_CN_STOCK_A.rein_payable'}, {'使用权资产': 'balance_sheet_CN_STOCK_A.right_of_use_assets'}, {'可供出售金融资产': 'balance_sheet_CN_STOCK_A.saleable_finacial_assets'}, {'吸收存款及同业存放': 'balance_sheet_CN_STOCK_A.saving_and_interbank_deposit'}, {' 结算备付金': 'balance_sheet_CN_STOCK_A.settle_reserves'}, {'专项应付款': 'balance_sheet_CN_STOCK_A.special_payable'}, {'应付短期债券': 'balance_sheet_CN_STOCK_A.st_bond_payable'}, {'短期借款': 'balance_sheet_CN_STOCK_A.st_borrow'}, {'应交税费': 'balance_sheet_CN_STOCK_A.tax_payable'}, {'资产总计': 'balance_sheet_CN_STOCK_A.total_assets'}, {'流动资产合计': 'balance_sheet_CN_STOCK_A.total_current_assets'}, {'流动负债合计': 'balance_sheet_CN_STOCK_A.total_current_liab'}, {'归属于母公司所有者权益合计': 'balance_sheet_CN_STOCK_A.total_equity_atoopc'}, {'负债和所有者权益总计': 'balance_sheet_CN_STOCK_A.total_liab_and_owner_equity'}, {'负债合计': 'balance_sheet_CN_STOCK_A.total_liab'}, {'非流动资产合计': 'balance_sheet_CN_STOCK_A.total_noncurrent_assets'}, {'非流动负债合计': 'balance_sheet_CN_STOCK_A.total_noncurrent_liab'}, {'所有者权益合计': 'balance_sheet_CN_STOCK_A.total_owner_equity'}, {'交易性金融资产': 'balance_sheet_CN_STOCK_A.tradable_fnncl_assets'}, {'交易性金融负债': 'balance_sheet_CN_STOCK_A.tradable_fnncl_liab'}, {'库存股': 'balance_sheet_CN_STOCK_A.treasury_stock'}, {'未分配利润': 'balance_sheet_CN_STOCK_A.undstrbtd_profit'}, {'证券代码': 'basic_info_CN_STOCK_A.instrument'}, {'公司类型': 'basic_info_CN_STOCK_A.company_type'}, {'公司名称': 'basic_info_CN_STOCK_A.company_name'}, {'公司省份': 'basic_info_CN_STOCK_A.company_province'}, {'上市 板': 'basic_info_CN_STOCK_A.list_board'}, {'公司成立日期': 'basic_info_CN_STOCK_A.company_found_date'}, {'证券名称': 'basic_info_CN_STOCK_A.name'}, {'上市日期': 'basic_info_CN_STOCK_A.list_date'}, {'公告日': 'cash_flow_CN_STOCK_A.date'}, {'股票代码': 'cash_flow_CN_STOCK_A.instrument'}, {'报告期': 'cash_flow_CN_STOCK_A.report_date'}, {'对应 季度': 'cash_flow_CN_STOCK_A.fs_quarter_index'}, {'资产减值准备': 'cash_flow_CN_STOCK_A.asset_impairment_reserve'}, {'向中央银行借款净增加额': 'cash_flow_CN_STOCK_A.borrowing_net_add_central_bank'}, {'拆入资金净增加额': 'cash_flow_CN_STOCK_A.borrowing_net_increase_amt'}, {'支付原保险合同赔付款项的现金': 'cash_flow_CN_STOCK_A.cash_of_orig_ic_indemnity'}, {
    #     '支付保单红利的现金': 'cash_flow_CN_STOCK_A.cash_paid_for_pd'}, {'支付给职工以及为职工支付的现金': 'cash_flow_CN_STOCK_A.cash_paid_to_staff_etc'}, {'偿还债 务支付的现金': 'cash_flow_CN_STOCK_A.cash_pay_for_debt'}, {'发行债券收到的现金': 'cash_flow_CN_STOCK_A.cash_received_from_bond_issue'}, {'收到原保险合同保费取得的现金': 'cash_flow_CN_STOCK_A.cash_received_from_orig_ic'}, {'吸收投资收到的现金': 'cash_flow_CN_STOCK_A.cash_received_of_absorb_invest'}, {'取得借款收到的现金': 'cash_flow_CN_STOCK_A.cash_received_of_borrowing'}, {'收回投资收到的现金': 'cash_flow_CN_STOCK_A.cash_received_of_dspsl_invest'}, {'收到其他与投资活动有关的现金': 'cash_flow_CN_STOCK_A.cash_received_of_other_fa'}, {'收到其他与经营活动有关的现金': 'cash_flow_CN_STOCK_A.cash_received_of_other_oa'}, {'收到其他与筹资活动有关的现金': 'cash_flow_CN_STOCK_A.cash_received_of_othr_fa'}, {'一年内到期的可转换公司债券': 'cash_flow_CN_STOCK_A.cb_due_within1y'}, {'子公司吸收少数股东投资收到的现金': 'cash_flow_CN_STOCK_A.cr_from_minority_holders'}, {'信用减值损失': 'cash_flow_CN_STOCK_A.credit_impairment_loss'}, {'债务转为资本': 'cash_flow_CN_STOCK_A.debt_tranfer_to_capital'}, {'客户存款和同业存放款项净增加额': 'cash_flow_CN_STOCK_A.deposit_and_interbank_net_add'}, {'递延所得税资产减少': 'cash_flow_CN_STOCK_A.dt_assets_decrease'}, {'递延所得税负债增加': 'cash_flow_CN_STOCK_A.dt_liab_increase'}, {'汇率变动对现金及现金等价物的影响': 'cash_flow_CN_STOCK_A.effect_of_exchange_chg_on_cce'}, {'现金的期末余额': 'cash_flow_CN_STOCK_A.ending_balance_of_cash'}, {'期末现金及现金等价物余额': 'cash_flow_CN_STOCK_A.final_balance_of_cce'}, {'融资租入固定资产': 'cash_flow_CN_STOCK_A.finance_lease_fixed_assets'}, {'固定资产报废损失': 'cash_flow_CN_STOCK_A.fixed_assets_scrap_loss'}, {'经营性应付项目的增加': 'cash_flow_CN_STOCK_A.increase_of_operating_item'}, {'现金的期初余额': 'cash_flow_CN_STOCK_A.initial_balance_of_cash'}, {'现金等价物的期初余额': 'cash_flow_CN_STOCK_A.initial_balance_of_cce'}, {'期初现金及现金等价物余额': 'cash_flow_CN_STOCK_A.initial_cce_balance'}, {'无形资产摊销': 'cash_flow_CN_STOCK_A.intangible_assets_amortized'}, {'存货的减少': 'cash_flow_CN_STOCK_A.inventory_decrease'}, {'取得投资收益收到的现金': 'cash_flow_CN_STOCK_A.invest_income_cash_received'}, {'投资损失': 'cash_flow_CN_STOCK_A.invest_loss'}, {'投资支付的现金': 'cash_flow_CN_STOCK_A.invest_paid_cash'}, {'向其他金融机构拆入资金净增加额': 'cash_flow_CN_STOCK_A.lending_net_add_other_org'}, {'客户贷款及垫款净增加额': 'cash_flow_CN_STOCK_A.loan_and_advancenet_add'}, {'公允价值变动损失': 'cash_flow_CN_STOCK_A.loss_from_fv_chg'}, {'长期待摊费用摊销': 'cash_flow_CN_STOCK_A.It_deferred_expenses_amrtzt'}, {'存放中央银行和同业款项净增加额': 'cash_flow_CN_STOCK_A.naa_of_cb_and_interbank'}, {'处置以公允价值计量且其变动计入当期损益的金融资产净增加额': 'cash_flow_CN_STOCK_A.naa_of_disposal_fnncl_assets'}, {'保户储金及投资款净增加额': 'cash_flow_CN_STOCK_A.naaassured_saving_and_invest'}, {'筹资活动产生的现金流量净额': 'cash_flow_CN_STOCK_A.ncf_from_fa'}, {'投资活动产生的现金流量净额': 'cash_flow_CN_STOCK_A.ncf_from_ia'}, {'经营活动产生的现金流量净额': 'cash_flow_CN_STOCK_A.ncf_from_oa'}, {'质押贷款净增加额': 'cash_flow_CN_STOCK_A.net_add_in_pledge_loans'}, {'回购业务资金净增加额': 'cash_flow_CN_STOCK_A.net_add_in_repur_capital'}, {'取得子公司及其他营业单位支付的现金净额': 'cash_flow_CN_STOCK_A.net_cash_amt_from_branch'}, {'处置子公司及其他营 业单位收到的现金净额': 'cash_flow_CN_STOCK_A.net_cash_of_disposal_branch'}, {'收到再保业务现金净额': 'cash_flow_CN_STOCK_A.net_cash_received_from_rein'}, {'现金及现金等价 物净增加额': 'cash_flow_CN_STOCK_A.net_increase_in_cce'}, {'经营性应收项目的减少': 'cash_flow_CN_STOCK_A.operating_items_decrease'}, {'支付其他与投资活动有关的现金': 'cash_flow_CN_STOCK_A.other_cash_paid_related_to_ia'}, {'支付其他与经营活动有关的现金': 'cash_flow_CN_STOCK_A.other_cash_paid_related_to_oa'}, {'支付其他与筹资活动有关的现金': 'cash_flow_CN_STOCK_A.othrcash_paid_relating_to_fa'}, {'支付的各项税费': 'cash_flow_CN_STOCK_A.payments_of_all_taxes'}, {'收到的税费返还': 'cash_flow_CN_STOCK_A.refund_of_tax_and_levies'}, {'现金等价物的期末余额': 'cash_flow_CN_STOCK_A.si_final_balance_of_cce'}, {'其他': 'cash_flow_CN_STOCK_A.si_other'}, {'筹资活动现金流入小计': 'cash_flow_CN_STOCK_A.sub_total_of_ci_from_fa'}, {'投资活动现金流入小计': 'cash_flow_CN_STOCK_A.sub_total_of_ci_from_ia'}, {'经营活动现金流入小计': 'cash_flow_CN_STOCK_A.sub_total_of_ci_from_oa'}, {'筹资活动现金流出小计': 'cash_flow_CN_STOCK_A.sub_total_of_cos_from_fa'}, {'投资活动现金流出小计': 'cash_flow_CN_STOCK_A.sub_total_of_cos_from_ia'}, {'经营活动现金流出小计': 'cash_flow_CN_STOCK_A.sub_total_of_cos_from_oa'}, {'日期': 'income_CN_STOCK_A.date'}, {'股票代码': 'income_CN_STOCK_A.instrument'}, {'报告期': 'income_CN_STOCK_A.report_date'}, {'对应季度': 'income_CN_STOCK_A.fs_quarter_index'}, {'以摊余成本计量的金融资产终止确认收益': 'income_CN_STOCK_A.amortized_cost_fnncl_ass_cfrm'}, {'重新计量设定受益计划净负债或净资产的变动': 'income_CN_STOCK_A.asset_change_due_to_remeasure'}, {'资产处置收益': 'income_CN_STOCK_A.asset_disposal_gain'}, {'资产减值损失': 'income_CN_STOCK_A.asset_impairment_loss'}, {'基本每股收益': 'income_CN_STOCK_A.basic_eps'}, {'权益法下在被投资单位不能重分类进损益的其他综合收益中享有的份额': 'income_CN_STOCK_A.cannt_reclass_gal_equity_law'}, {'以后不能重分类进损益的其他综合收益': 'income_CN_STOCK_A.cannt_reclass_to_gal'}, {'现金流量套期储备': 'income_CN_STOCK_A.cash_flow_hedge_reserve'}, {'现金流量套期损益的有效部分': 'income_CN_STOCK_A.cf_hedging_gal_valid_part'}, {'手续费及佣金支出': 'income_CN_STOCK_A.charge_and_commi_expenses'}, {'保单红利支出': 'income_CN_STOCK_A.commi_on_insurance_policy'}, {'赔付支出净额': 'income_CN_STOCK_A.compensate_net_pay'}, {'企业自身信用风险公允价值变动': 'income_STOCK_A.earned_premium'}, {'汇兑收益': 'income_CN_STOCK_A.exchange_gain'}, {'提取保险合同准备金净额': 'income_CN_STOCK_A.extract_ic_reserve_net_amt'}, {'金融资产重分类计入其他综合收益的金额': 'income_CN_STOCK_A.fa_reclassi_amt'}, {'外币财务报表折算差额': 'income_CN_STOCK_A.fc_convert_diff'}, {'手续费及佣金收入': 'income_CN_STOCK_A.fee_and_commi_income'}, {'财务费用': 'income_CN_STOCK_A.financing_expenses'}, {'公允价值变动收益': 'income_CN_STOCK_A.fv_chg_income'}, {'对联营企业和合营企业的投资收益': 'income_CN_STOCK_A.ii_from_jc_etc'}, {'所 得税费用': 'income_CN_STOCK_A.income_tax_cost'}, {'利息收入': 'income_CN_STOCK_A.interest_income'}, {'利息支出': 'income_CN_STOCK_A.interest_payout'}, {'投资收益': 'income_CN_STOCK_A.invest_income'}, {'管理费用': 'income_CN_STOCK_A.manage_fee'}, {'少数股东损益': 'income_CN_STOCK_A.minority_gal'}, {'净敞口套期收益': 'income_CN_STOCK_A.net_open_hedge_income'}, {' 营业外收入': 'income_CN_STOCK_A.non_operating_income'}, {'非流动资产处置利得': 'income_CN_STOCK_A.noncurrent_asset_dispose_gain'}, {'非流动资产处置损失': 'income_CN_STOCK_A.noncurrent_asset_dispose_loss'}, {'营业外支出': 'income_CN_STOCK_A.nonoperating_cost'}, {'归属于母公司所有者的净利润': 'income_CN_STOCK_A.np_atoopc'}, {'营业成本': 'income_CN_STOCK_A.operating_cost'}, {'税金及附加': 'income_CN_STOCK_A.operating_taxes_and_surcharge'}, {'营业总成本': 'income_CN_STOCK_A.operating_total_cost'}, {'营业总收入': 'income_CN_STOCK_A.operating_total_revenue'}, {'其他综合收益': 'income_CN_STOCK_A.other_compre_income'}, {'其他债权投资公允价值变动': 'income_CN_STOCK_A.other_debt_right_invest_fvc'}, {'其他债权投资信用减值准备': 'income_CN_STOCK_A.other_debt_right_invest_ir'}, {'其他权益工具投资公允价值变动': 'income_CN_STOCK_A.other_equity_invest_fvc'}, {'其他收益': 'income_CN_STOCK_A.other_income'}, {'其他 以后不能重分类进损益': 'income_CN_STOCK_A.other_not_reclass_to_gal'}, {'其他以后将重分类进损益': 'income_CN_STOCK_A.other_reclass_to_gal'}, {'归属于少数股东的其他综合收益': 'income_CN_STOCK_A.othrcompre_income_atms'}, {'归属母公司所有者的其他综合收益': 'income_CN_STOCK_A.othrcompre_income_atoopc'}, {'研发费用': 'income_CN_STOCK_A.rad_cost_sum'}, {'持有至到期投资重分类为可供出售金融资产损益': 'income_CN_STOCK_A.reclass_and_salable_gal'}, {'以后将重分类进损益的其他综合收益': 'income_CN_STOCK_A.reclass_to_gal'}, {'权益法下在被投资单位以后将重 分类进损益的其他综合收益中享有的份额': 'income_CN_STOCK_A.reclass_togal_in_equity_law'}, {'退保金': 'income_CN_STOCK_A.refunded_premium'}, {'分保费用': 'income_CN_STOCK_A.rein_expenditure'}, {'营业收入': 'income_CN_STOCK_A.revenue'}, {'可供出售金融资产公允价值变动损益': 'income_CN_STOCK_A.saleable_fv_chg_gal'}, {'销售费用': 'income_CN_STOCK_A.sales_fee'}, {'归属于母公司股东的综合收益总额': 'income_CN_STOCK_A.total_compre_income_atsopc'}, {'综合收益总额': 'income_CN_STOCK_A.total_compre_income'}, {'利润总额': 'income_CN_STOCK_A.total_profit'}]
    # start_time = time.time()
    # results, selected_tables_and_columns = get_table_and_columns_by_similarity(
    #     embedder, fields, comments_list)
    # print(time.time() - start_time)
    # print(results)
    # print(selected_tables_and_columns)
    # start_time = time.time()
    # results, selected_tables_and_columns = get_table_and_columns_by_fuzzy_similarity(
    #     fields, comments_list)
    # print(time.time() - start_time)
    # print(results)
    # print(selected_tables_and_columns)
