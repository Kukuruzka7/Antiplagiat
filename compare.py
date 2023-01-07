import ast


def parse_arguments():
    import argparse
    parser = argparse.ArgumentParser(description='process args')
    parser.add_argument('input_file', metavar='input_file', type=argparse.FileType('r'),
                        help='input file with pairs of files to compare')
    parser.add_argument('output_file', metavar='output_file', type=argparse.FileType('w'),
                        help='output file to which to write the result')
    args = vars(parser.parse_args())
    return args['input_file'], args['output_file']


def remove_doc(ast_tree: ast.AST):
    for node in ast.walk(ast_tree):
        if not isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef, ast.Module)) or len(node.body) == 0:
            continue
        if not isinstance(node.body[0], ast.Expr):
            continue
        if hasattr(node.body[0], 'value') and isinstance(node.body[0].value, ast.Str):
            node.body = node.body[1:]
        if hasattr(node.body[0], 'value') and isinstance(node.body[0].value, ast.Constant):
            node.body = node.body[1:]


class TypeHintRemover(ast.NodeTransformer):

    def visit_FunctionDef(self, node):
        node.returns = None
        if node.args.args:
            for arg in node.args.args:
                arg.annotation = None
        return node


class Renamer(ast.NodeTransformer):
    def __init__(self):
        self.level = 0
        self.func_dict = {}
        self.func_count = 0
        self.class_dict = {}
        self.class_count = 0

    def visit_FunctionDef(self, node):
        self.level += 1
        ast.NodeVisitor.generic_visit(self, node)
        self.level -= 1
        self.func_dict[node.name] = "func_{}".format(self.func_count)
        node.name = "func_{}".format(self.func_count)
        self.func_count += 1
        return node

    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        self.level += 1
        ast.NodeVisitor.generic_visit(self, node)
        self.level -= 1
        self.class_dict[node.name] = "class_{}".format(self.class_count)
        node.name = "class_{}".format(self.class_count)
        self.class_count += 1
        return node

    def visit_Call(self, node):
        self.level += 1
        ast.NodeVisitor.generic_visit(self, node)
        node.args = [self.visit(arg) for arg in node.args]
        node.keywords = [self.visit(kw) for kw in node.keywords]
        self.level -= 1
        if hasattr(node.func, 'id'):
            if node.func.id in self.func_dict:
                node.func = ast.Name(**{**node.__dict__, 'id': self.func_dict[node.func.id]})
            elif node.func.id in self.class_dict:
                node.func = ast.Name(**{**node.__dict__, 'id': self.class_dict[node.func.id]})
            else:
                node.func = ast.Name(**{**node.__dict__, 'id': "name_{}".format(self.level)})
        return node

    def visit_arg(self, node):
        return ast.arg(**{**node.__dict__, 'arg': "arg_{}".format(self.level)})

    def visit_keyword(self, node):
        ast.NodeVisitor.generic_visit(self, node)
        return ast.keyword(**{**node.__dict__, 'arg': "keyword_{}".format(self.level)})

    def visit_Attribute(self, node):
        ast.NodeVisitor.generic_visit(self, node)
        node.value = ast.Name(**{**node.__dict__, 'id': "name_{}".format(self.level)})
        node.attr = "attr_{}".format(self.level)
        return node

    def visit_Name(self, node):
        return ast.Name(**{**node.__dict__, 'id': "name_{}".format(self.level)})


def normalize(lines: str) -> str:
    code_tree = ast.parse(lines)
    remove_doc(code_tree)
    code_tree = TypeHintRemover().visit(code_tree)
    code_tree = Renamer().visit(code_tree)
    return ast.unparse(code_tree)


def similar(line1: str, line2: str) -> bool:
    n, m = len(line1), len(line2)
    if n > m:
        line1, line2 = line2, line1
        n, m = m, n
    now = range(n + 1)
    for i in range(1, m + 1):
        prev, now = now, [i] + [0] * n
        for j in range(1, n + 1):
            add, delete, change = prev[j] + 1, now[j - 1] + 1, prev[j - 1]
            if line1[j - 1] != line2[i - 1]:
                change += 1
            now[j] = min(add, delete, change)
    if m != 0:
        return now[n] / m <= 0.3
    else:
        return True


BLOCK_SIZE: int = 1


def make_blocks(text: [str]) -> [str]:
    if len(text) >= BLOCK_SIZE:
        blocks = []
        for i in range(len(text)):
            if i + BLOCK_SIZE <= len(text) and i % BLOCK_SIZE in [0, BLOCK_SIZE // 2]:
                blocks.append("\n".join(text[i:i + BLOCK_SIZE]))
        return blocks
    else:
        return text.copy()


def levenshtein(text1: [str], text2: [str]) -> float:
    blocks1 = make_blocks(text1)
    blocks2 = make_blocks(text2)
    n, m = len(blocks1), len(blocks2)
    if n > m:
        blocks1, blocks2 = blocks2, blocks1
        n, m = m, n
    now = range(n + 1)
    for i in range(1, m + 1):
        prev, now = now, [i] + [0] * n
        for j in range(1, n + 1):
            add, delete, change = prev[j] + 1, now[j - 1] + 1, prev[j - 1]
            if not similar(blocks1[j - 1], blocks2[i - 1]):
                change += 1
            now[j] = min(add, delete, change)
    if m != 0:
        return now[n] / m
    else:
        return 0.0


def compare(name1: str, name2: str) -> float:
    try:
        file1 = open(name1)
        file2 = open(name2)
    except IOError:
        return -1.0
    else:
        with file1, file2:
            text1 = normalize(''.join(file1.readlines())).split('\n')
            text2 = normalize(''.join(file2.readlines())).split('\n')
            return 1.0 - levenshtein(text1, text2)


if __name__ == '__main__':
    input_file, output_file = parse_arguments()
    try:
        for line in input_file:
            file_name1, file_name2 = line.split()
            result = compare(file_name1, file_name2)
            print(result)
            if result == -1.0:
                output_file.write("Problems with code-files\n")
            else:
                output_file.write(f"{result}\n")
    finally:
        input_file.close()
        output_file.close()
