import numpy
from sentence_transformers import SentenceTransformer, util
from thefuzz import fuzz
from difflib import SequenceMatcher


def calculate_similarity(embedder: SentenceTransformer, text1: str, text2: str) -> float:

    # Tokenize and encode the texts
    encoding1 = embedder.encode(text1)
    encoding2 = embedder.encode(text2)

    # Calculate the cosine similarity between the embeddings
    similarity = numpy.dot(encoding1, encoding2) / \
        (numpy.linalg.norm(encoding1) * numpy.linalg.norm(encoding2))
    # Compute cosine-similarities
    # similarity = util.cos_sim(encoding1, encoding2)
    return similarity


def fuzzy_similarity(text1: str, text2: str) -> float:
    similarity = fuzz.ratio(text1, text2) / 100
    return similarity


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def str_similarity(s1, s2):
    # 计算字符串长度
    m = len(s1)
    n = len(s2)
    # 初始化编辑距离矩阵
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    # 计算编辑距离
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
    # 计算最大相似性（两个字符串长度之和）
    max_similarity = m + n
    # 计算归一化相似性分数
    normalized_similarity = 1 - (dp[m][n] / max_similarity)
    return normalized_similarity


if __name__ == "__main__":
    text1 = "退市日期"
    text2 = "退市日期，如果未退市，则为pandas.NaT"
    text3 = "退保金"
    text4 = "拆出资金"
    text5 = "固定资产清理"
    # embedder = SentenceTransformer(
    #     'sentence-transformers/all-mpnet-base-v2')
    # similarity = calculate_similarity(embedder, text1, text2)
    # similarity2 = calculate_similarity(embedder, text1, text3)
    # similarity3 = calculate_similarity(embedder, text1, text4)
    # similarity4 = calculate_similarity(embedder, text1, text5)
    # print(similarity)
    # print(similarity2)
    # print(similarity3)
    # print(similarity4)
    # print(fuzzy_similarity(text1, text2))
    # print(fuzzy_similarity(text1, text3))
    # print(fuzzy_similarity(text1, text4))
    # print(fuzzy_similarity(text1, text5))
    # print(similar(text1, text2))
    # print(similar(text1, text3))
    # print(similar(text1, text4))
    # print(similar(text1, text5))
    # print(str_similarity(text1, text2))
    # print(str_similarity(text1, text3))
    # print(str_similarity(text1, text4))
    # print(str_similarity(text1, text5))
