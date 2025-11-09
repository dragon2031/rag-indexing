
def main():
    print("Hello from rag_indexing!")

    sentece="""上周（2025.10.27-2025.11.2）30 大中城市房地产新房成交面积 201.93 万平方米，同比下跌 39.22%，环比上涨 1%。其中一线城市成交面积 48.06 万平方米，同比下跌 55.04%，二线城市成交面积 113 万平方米，同比下跌 33.46%，三线城市成交面积 40.87 万平方米，同比下跌 26.36%。  
            __IMAGE_BLOCK_0__  
            30 大中城市房地产新房累计成交面积 7473.55 万平方米，同比下跌 6.8%。  
            __IMAGE_BLOCK_1__"""
    flag='\n__IMAGE_BLOCK_0__\n' in sentece
    if flag:
        print("flag is true")
    else:
        print("flag is false")

if __name__ == "__main__":
    main()