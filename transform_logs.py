import ast
import sys

def transform_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    
    tree = ast.parse(source)
    
    # Find all logger.log calls
    class LoggerLogTransformer(ast.NodeTransformer):
        def visit_Call(self, node):
            # Check if it's self.logger.log(...)
            if (isinstance(node.func, ast.Attribute) and node.func.attr == 'log'
                and isinstance(node.func.value, ast.Attribute) and node.func.value.attr == 'logger'
                and isinstance(node.func.value.value, ast.Name) and node.func.value.value.id == 'self'):
                # Change to print
                node.func.attr = 'print'
                
                # Transform keyword arguments
                new_keywords = []
                for kw in node.keywords:
                    if kw.arg == 'text_color':
                        kw.arg = 'color'
                        new_keywords.append(kw)
                    elif kw.arg in ('level_color', 'bracket_color'):
                        # ignore these arguments
                        continue
                    else:
                        new_keywords.append(kw)
                node.keywords = new_keywords
                # Note: we keep level, tag, etc as is
                # Also ensure message is first positional arg; we don't change order
                # No need to adjust
                return node
            return self.generic_visit(node)
    
    transformer = LoggerLogTransformer()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)
    
    # Convert back to source
    # Use ast.unparse if available (Python 3.9+)
    try:
        new_source = ast.unparse(new_tree)
    except AttributeError:
        # Fallback: use codegen? We'll implement simple unparse for our case.
        # For simplicity, we'll just write a simple unparse that works for our limited case.
        # But we assume Python 3.9+.
        raise RuntimeError('Python version does not support ast.unparse')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_source)
    print(f'Transformed {filepath}')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python transform_logs.py <file1> [file2 ...]')
        sys.exit(1)
    for filepath in sys.argv[1:]:
        transform_file(filepath)
