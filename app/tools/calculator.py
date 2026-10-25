
import ast
import math
import operator


OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def calculate(expression: str) -> dict:
    """Evaluate a simple arithmetic expression safely."""

    if len(expression) > 100:
        raise ValueError("Expression is too long.")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid expression.") from exc

    def evaluate(node, depth=0):
        if depth > 12:
            raise ValueError("Expression is too complex.")

        if isinstance(node, ast.Constant):
            if type(node.value) is int:
                value = float(node.value)
            elif type(node.value) is float:
                value = node.value
            else:
                raise ValueError("Only numbers are allowed.")

        elif isinstance(node, ast.BinOp):
            if type(node.op) not in OPERATORS:
                raise ValueError("Operator not allowed.")

            left = evaluate(node.left, depth + 1)
            right = evaluate(node.right, depth + 1)

            if isinstance(node.op, ast.Div) and right == 0:
                raise ValueError("Division by zero.")

            value = OPERATORS[type(node.op)](left, right)

        elif isinstance(node, ast.UnaryOp):
            number = evaluate(node.operand, depth + 1)

            if isinstance(node.op, ast.USub):
                value = -number
            elif isinstance(node.op, ast.UAdd):
                value = number
            else:
                raise ValueError("Operator not allowed.")

        else:
            raise ValueError("Expression not allowed.")

        if not math.isfinite(value) or abs(value) > 1e12:
            raise ValueError("Result exceeds allowed range.")

        return value

    result = evaluate(tree.body)

    return {
        "expression": expression,
        "result": result,
    }