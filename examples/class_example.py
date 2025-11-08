"""
Python 类定义示例
"""

class Person:
    """一个表示人的简单类"""
    
    # 类变量
    species = "Homo sapiens"
    
    def __init__(self, name, age):
        """
        初始化方法（构造函数）
        
        Args:
            name (str): 人的姓名
            age (int): 人的年龄
        """
        # 实例变量
        self.name = name
        self.age = age
    
    def introduce(self):
        """返回自我介绍的字符串"""
        return f"Hello, my name is {self.name} and I am {self.age} years old."
    
    def have_birthday(self):
        """增加年龄"""
        self.age += 1
    
    @classmethod
    def get_species(cls):
        """类方法 - 获取物种名称"""
        return cls.species
    
    @staticmethod
    def is_adult(age):
        """静态方法 - 判断是否成年"""
        return age >= 18


# 使用示例
if __name__ == "__main__":
    # 创建Person类的实例
    person1 = Person("Alice", 25)
    person2 = Person("Bob", 17)
    
    # 调用实例方法
    print(person1.introduce())
    print(person2.introduce())
    
    # 调用类方法
    print(f"Species: {Person.get_species()}")
    
    # 调用静态方法
    print(f"Alice is adult: {Person.is_adult(person1.age)}")
    print(f"Bob is adult: {Person.is_adult(person2.age)}")
    
    # 修改实例属性
    person1.have_birthday()
    print(f"After birthday: {person1.introduce()}")
