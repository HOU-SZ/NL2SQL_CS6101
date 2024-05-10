import re
from thefuzz import fuzz
from difflib import SequenceMatcher


def fix_sql(sql, column_values_dict):
    # 从SQL语句中提取列名和值
    columns_and_values = re.findall(r'(\w+)\s*=\s*\'([^\']*)\'', sql)

    # 对于每个列和对应的值
    for column, value in columns_and_values:
        # 检查该列是否在字典中，并且该值是否不在字典中对应列的取值列表中
        if column.strip() in column_values_dict and value.strip() not in column_values_dict[column.strip()]:
            # 寻找字典中对应列的取值列表中最相似的值
            closest_value, success = find_closest_value(
                value.strip(), column_values_dict[column.strip()])
            # 替换SQL语句中该列的值为最相似的值
            if success:
                sql = re.sub(rf'\b{re.escape(value)}\b', closest_value, sql)
            else:
                if column.strip() == "company_name":
                    sql = sql.replace("company_name =", "name =")
                    sql = sql.replace("company_name IN", "name IN")

    return sql


def find_closest_value(value, value_list):
    # 计算每个取值和目标值的相似度，并返回最相似的值
    closest_value = max(value_list, key=lambda x: fuzzy_similarity(value, x))
    if closest_value == "nan" or closest_value == "None":
        return value, False
    return closest_value, True


def fuzzy_similarity(text1: str, text2: str) -> float:
    similarity = fuzz.ratio(text1, text2) / 100
    return similarity


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def similarity(s1, s2):
    # 计算两个字符串的相似度（编辑距离）
    m = len(s1)
    n = len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        for j in range(n + 1):
            if i == 0:
                dp[i][j] = j
            elif j == 0:
                dp[i][j] = i
            elif s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i]
                                   [j - 1], dp[i - 1][j - 1])
    return dp[m][n]


if __name__ == "__main__":
    # 输入的SQL语句
    sql = "SELECT fee_and_commi_income FROM income_CN_STOCK_A INNER JOIN basic_info_CN_STOCK_A ON income_CN_STOCK_A.instrument = basic_info_CN_STOCK_A.instrument WHERE company_name = '比亚迪' AND company_province = '广东' AND YEAR(report_date) = 2022;"
    # 输入的字典
    column_values_dict = {
        "company_name": ["九号有限公司", "格力电器股份有限公司", "比亚迪股份有限公司", "平安银行股份有限公司"],
        "company_province": ["北京市", "上海市", "广东省"]
    }
    # 输入的SQL语句
    sql = "SELECT CASE WHEN basic_info_CN_STOCK_A.company_name = '华夏银行' THEN cash_flow_CN_STOCK_A.cash_received_of_other_oa END AS '华夏银行', CASE WHEN basic_info_CN_STOCK_A.company_name = '格力电器' THEN cash_flow_CN_STOCK_A.cash_received_of_other_oa END AS '格力电器' FROM cash_flow_CN_STOCK_A INNER JOIN basic_info_CN_STOCK_A ON cash_flow_CN_STOCK_A.instrument = basic_info_CN_STOCK_A.instrument WHERE basic_info_CN_STOCK_A.company_name IN ('华夏银行', '格力电器') AND cash_flow_CN_STOCK_A.report_date BETWEEN '2022-01-01' AND '2022-12-31';"
    # 输入的字典
    column_values_dict = {
        "company_name": ["九号有限公司", "格力电器股份有限公司", "比亚迪股份有限公司", "平安银行股份有限公司", "华夏银行股份有限公司", "中国平安股份有限公司", "长虹能源股份有限公司", "同享科技股份有限公司"],
        "company_province": ["北京市", "上海市", "广东省"]
    }
    # # 输入的SQL语句
    # sql = "SELECT T1.instrument, T1.financing_expenses > T2.financing_expenses AS higher_financing_expenses FROM ( SELECT T1.instrument, SUM(T2.financing_expenses) AS financing_expenses FROM basic_info_CN_STOCK_A AS T1 INNER JOIN income_CN_STOCK_A AS T2 ON T1.instrument = T2.instrument WHERE T1.company_name = '长虹能源' AND YEAR(T2.report_date) = 2022 GROUP BY T1.instrument ) AS T1 INNER JOIN ( SELECT T1.instrument, SUM(T2.financing_expenses) AS financing_expenses FROM basic_info_CN_STOCK_A AS T1 INNER JOIN income_CN_STOCK_A AS T2 ON T1.instrument = T2.instrument WHERE T1.company_name = '同享科技' AND YEAR(T2.report_date) = 2022 GROUP BY T1.instrument ) AS T2 WHERE T1.instrument = '长虹能源' AND T2.instrument = '同享科技';"
    # # 输入的字典
    # column_values_dict = {
    #     "company_name": ['nan', 'None', "格力电器股份有限公司", "比亚迪股份有限公司", "平安银行股份有限公司", "华夏银行股份有限公司", "中国平安股份有限公司", "长虹能源股份有限公司", "同享科技股份有限公司"],
    #     "company_province": ['None', "北京市", "上海市", "广东省"]
    # }

    # sql = "SELECT company_name, list_date FROM basic_info_CN_STOCK_A WHERE company_province = '广东省' AND YEAR(list_date) > 2000;"
    # column_values_dict = {
    #     "company_name": ['nan', 'None', "格力电器股份有限公司", "比亚迪股份有限公司", "平安银行股份有限公司", "华夏银行股份有限公司", "中国平安股份有限公司", "长虹能源股份有限公司", "同享科技股份有限公司"],
    #     "company_province": ['None', "北京市", "上海市", "广东省"]
    # }
    # remove_list = ['nan', 'None']
    # for key in column_values_dict:
    #     column_values_dict[key] = [
    #         x for x in column_values_dict[key] if x not in remove_list]
    # print(column_values_dict)

    # 调用函数修正SQL语句
    fixed_sql = fix_sql(sql, column_values_dict)

    # 输出修正的SQL语句
    print(fixed_sql)
