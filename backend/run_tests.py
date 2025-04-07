import unittest

def run_tests():
    """运行所有测试"""
    # 发现并运行所有测试
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests')
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(test_suite)

if __name__ == '__main__':
    run_tests() 