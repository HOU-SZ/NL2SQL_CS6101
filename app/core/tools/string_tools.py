import json
import ast


# convert the input string to a list of tuples
def convert_string_to_list(input_string):
    input_string = input_string.replace("[", "").replace("]", "")
    input_list = input_string.split("), ")
    output_list = []
    for item in input_list:
        item = item.replace("(", "").replace(")", "")
        current_tuple = []
        for field in item.split(", "):
            if field.isdigit():
                current_tuple.append(int(field))
            elif field[0] == "'" and field[-1] == "'":
                current_tuple.append(field[1:-1])
            elif field[0] == '"' and field[-1] == '"':
                current_tuple.append(field[1:-1])
            else:
                current_tuple.append(field)
        output_list.append(tuple(current_tuple))
    return output_list


def convert_dict_to_string(input_dict):
    output_string = "{\n"
    for key, value in input_dict.items():
        output_string += f"    '{key}': {json.dumps(value, ensure_ascii=False)},\n"
    output_string = output_string[:-2]  # Remove the last comma and newline
    output_string += "\n}"
    return output_string


if __name__ == "__main__":
    input_string = "[(1, 1987-12-22, 'AC/DC'), (2, 2012-12-20, 'Accept'), (3, 2012-12-20, 'Aerosmith'), (4, 2012-12-20, 'Alanis Morissette'), (5, 2012-12-20, 'Alice In Chains')]"

    # output_list = ast.literal_eval(input_string)
    # print(output_list)
    print(convert_string_to_list(input_string))

    input_dict = {
        'basic_info_CN_STOCK_A.instrument': ['002089.SZA', '002543.SZA', '300081.SZ', '688056.SHA', '603887.SHA', '830946.BJA', '832786.BJA', '000787.SZA'],
        'basic_info_CN_STOCK_A.company_name': ["珠海格力电器股份有限公司", "比亚迪股份有限公司", "平安银行股份有限公司", "华夏银行股份有限公司", "中国平安股份有限公司", "四川长虹新能源科技股份有限公司", "同享(苏州)电子材料科技股份有限公司", "东华能源股份有限公司", "同兴环保科技股份有限公司"],
        'basic_info_CN_STOCK_A.name': ['平安银行', '格力电器', '比亚迪', '长虹能源', '华夏银行', '中国平安', '同享科技', '东华能源', '同兴环保'],
    }
    output_string = convert_dict_to_string(input_dict)
    print(output_string)
