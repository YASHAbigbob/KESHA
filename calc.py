import re
from decimal import Decimal, getcontext, InvalidOperation, DivisionByZero, ROUND_HALF_UP


class ASTNode:
    pass


class NumberNode(ASTNode):
    def __init__(self, value: Decimal):
        self.value = value

    def evaluate(self, base=None, precision=None):
        return self.value


class BinaryOpNode(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def evaluate(self, base=None, precision=None):
        left_val = self.left.evaluate(base=base, precision=precision)

        # Для операций + и - передаем left_val как базу для правой части (для процентов)
        if self.op in ('+', '-'):
            right_val = self.right.evaluate(base=left_val, precision=precision)
        else:
            right_val = self.right.evaluate(precision=precision)

        if self.op == '+':
            result = left_val + right_val
        elif self.op == '-':
            result = left_val - right_val
        elif self.op == '*':
            result = left_val * right_val
        elif self.op == '/':
            if right_val == 0:
                raise DivisionByZero("Деление на ноль")
            result = left_val / right_val
        elif self.op == '**':
            try:
                if right_val == right_val.to_integral_value():
                    exp = int(right_val)
                    result = left_val ** exp
                else:
                    raise ValueError("Дробные степени не поддерживаются в денежных расчётах")
            except (ValueError, OverflowError) as e:
                raise ValueError(f"Невозможно вычислить степень: {e}")

        # Округление результата бинарной операции
        if precision is not None:
            result = result.quantize(Decimal('1.' + '0' * precision), rounding=ROUND_HALF_UP)

        return result


class PercentNode(ASTNode):
    def __init__(self, value_node):
        self.value_node = value_node

    def evaluate(self, base=None, precision=None):
        percent_val = self.value_node.evaluate(precision=precision)

        if base is not None:
            # Бытовой процент: base * (percent / 100)
            result = base * (percent_val / Decimal('100'))
        else:
            # Изолированный процент: percent / 100
            result = percent_val / Decimal('100')

        # Округление результата процентной операции
        if precision is not None:
            result = result.quantize(Decimal('1.' + '0' * precision), rounding=ROUND_HALF_UP)

        return result


class UnaryOpNode(ASTNode):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

    def evaluate(self, base=None, precision=None):
        val = self.operand.evaluate(precision=precision)
        if self.op == '+':
            result = val
        elif self.op == '-':
            result = -val

        # Округление результата унарной операции
        if precision is not None:
            result = result.quantize(Decimal('1.' + '0' * precision), rounding=ROUND_HALF_UP)

        return result


class PercentageCalculator:
    def __init__(self, precision=2):
        self.token = None
        self.tokens = []
        self.pos = 0
        self.precision = precision
        self.set_precision(precision)

    def set_precision(self, precision):
        """Установить количество знаков после запятой"""
        if precision < 0:
            raise ValueError("Точность не может быть отрицательной")
        self.precision = precision
        getcontext().prec = max(28, precision + 10)

    def tokenize(self, expression):
        # ДОБАВЛЯЕМ ЗАМЕНУ : НА / ДЛЯ ПОДДЕРЖКИ ДЕЛЕНИЯ ЧЕРЕЗ ДВОЕТОЧИЕ
        expression = expression.replace(' ', '').replace('^', '**').replace(':', '/')
        tokens = re.findall(r'''
            (\d+\.?\d*|\.\d+|   # числа: 123, 12.3, .5
            \*\*|                # **
            [+\-*/()%]|
            $|$)''', expression, re.VERBOSE)
        return [t for t in tokens if t]

    def parse(self, expression):
        self.tokens = self.tokenize(expression)
        self.pos = 0
        self.next_token()
        ast = self.parse_expression()
        if self.token is not None:
            raise ValueError(f"Неожиданный токен: {self.token}")
        return ast

    def next_token(self):
        if self.pos < len(self.tokens):
            self.token = self.tokens[self.pos]
            self.pos += 1
        else:
            self.token = None

    def parse_expression(self):
        left = self.parse_term()
        while self.token in ('+', '-'):
            op = self.token
            self.next_token()
            right = self.parse_term()
            left = BinaryOpNode(left, op, right)
        return left

    def parse_term(self):
        left = self.parse_power()
        while self.token in ('*', '/'):
            op = self.token
            self.next_token()
            right = self.parse_power()
            left = BinaryOpNode(left, op, right)
        return left

    def parse_power(self):
        left = self.parse_factor()
        if self.token == '**':
            self.next_token()
            right = self.parse_power()
            left = BinaryOpNode(left, '**', right)
        return left

    def parse_factor(self):
        if self.token == '+':
            self.next_token()
            return UnaryOpNode('+', self.parse_factor())
        elif self.token == '-':
            self.next_token()
            return UnaryOpNode('-', self.parse_factor())
        elif self.token == '(':
            self.next_token()
            expr = self.parse_expression()
            if self.token != ')':
                raise ValueError("Ожидается )")
            self.next_token()
            return expr
        elif self.token is not None and self._is_number(self.token):
            try:
                num = Decimal(self.token)
            except InvalidOperation:
                raise ValueError(f"Некорректное число: {self.token}")
            self.next_token()
            node = NumberNode(num)
            if self.token == '%':
                self.next_token()
                return PercentNode(node)
            return node
        else:
            raise ValueError(f"Неожиданный токен: {self.token}")

    def _is_number(self, token):
        try:
            Decimal(token)
            return True
        except InvalidOperation:
            return False

    def calculate(self, expression, precision=None):
        """
        Вычислить выражение с указанной точностью

        Args:
            expression: математическое выражение
            precision: количество знаков после запятой (None - использовать установленную)
        """
        if precision is None:
            precision = self.precision

        try:
            # ДОБАВЛЯЕМ ПРОВЕРКУ НА ПУСТОЕ ВЫРАЖЕНИЕ
            if not expression.strip():
                return "Ошибка: пустое выражение"

            ast = self.parse(expression)
            result = ast.evaluate(precision=precision)

            if isinstance(result, Decimal):
                # Окончательное округление
                if precision is not None:
                    result = result.quantize(Decimal('1.' + '0' * precision), rounding=ROUND_HALF_UP)

                result = result.normalize()
                s = format(result, 'f')

                # Убираем лишние нули после запятой
                if '.' in s:
                    s = s.rstrip('0').rstrip('.')
                    # Если precision > 0 и нет десятичной части, добавляем . и нули
                    if precision > 0 and '.' not in s:
                        s += '.' + '0' * precision
                    elif '.' in s:
                        current_precision = len(s.split('.')[1])
                        if current_precision < precision:
                            s += '0' * (precision - current_precision)
                elif precision > 0:
                    s += '.' + '0' * precision

                return s
            else:
                return str(result)
        except DivisionByZero:
            return "Ошибка: деление на ноль"
        except InvalidOperation:
            return "Ошибка: недопустимая операция"
        except Exception as e:
            return f"Ошибка: {str(e)}"


# Функция для обратной совместимости
def def_calc(expression: str, precision: int = 2) -> str:
    calculator = PercentageCalculator(precision)
    return calculator.calculate(expression, precision)


# Тестовый код
if __name__ == "__main__":
    test_expressions = [
        "2+2",
        "100-50%",
        "(100+50)*2",
        "100:4",
        "100 + 50 + 2%"
    ]

    for expr in test_expressions:
        result = def_calc(expr)
        print(f"{expr} = {result}")