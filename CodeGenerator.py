from os import path
import re

'''
Todo:
1. Template inheritance and inclusion
2. Custom tags
3. Automatic escaping
4. Arguments to filters
5. Complex conditional logic like else and elif
6. Loops with more than one loop variable
7. Whitespace control
'''

class CodeBuilder(object):
    """Build source code conveniently"""

    def __init__(self, indent=0):
        self.code = []
        self.indent_level = indent
        self.INDENT_STEP = 4

    def add_line(self, line):
        """Add a line of source to the code.
        Indentation and newline will be added for you, don't provide them
        add_line("add")->^^^^add\n
        """

        self.code.extend([" " * self.indent_level, line, "\n"])

    def indent(self):
        """Increase the current indent for following lines."""
        self.indent_level += self.INDENT_STEP

    def dedent(self):
        """Decrease the current indent for following lines."""
        self.indent_level -= self.INDENT_STEP

    def add_section(self):
        """Add a section, a sub-CodeBuilder"""
        section = CodeBuilder(self.indent_level)
        self.code.append(section)
        return section

    def __str__(self):
        return "".join(str(c) for c in self.code)

    def get_globals(self):
        """Execute the code, and return a dict of globals it defines"""
        # A check that the caller really finished.
        assert self.indent_level == 0
        # Get the Python source as a single string.
        # 这里会通过__str__把子对象的code也转变成string
        python_source = str(self)

        # Execute the source, defining globals, and return them.
        global_namespace = {}
        exec(python_source, global_namespace)
        return global_namespace


class Templite(object):
    def __init__(self, text, *contexts):
        """Construct a Templite with given `text`.
        `contexts` are dictionaries of values to use for future renderings
        These are good for filters and global values

        """
        self.context = {}
        for context in contexts:
            self.context.update(context)
        # 所有变量集合，包含局部变量
        self.all_vars = set()
        # 局部变量集合
        self.loop_vars = set()

        ops_stack = []
        # 将模板分成块
        """
        比如：模板
        <p>Welcome, {{user_name}}!</p>
        <p>Products:</p>
        <ul>
        {% for product in product_list %}
                <li>{{ product.name }}: {{ product.price|format_price }}</li>
        {% endfor %}
        </ul>
        会转变转变成下面列表
        ['\n<p>Welcome, ', '{{user_name}}', '!</p>\n<p>Products:</p>\n<ul>\n',
         '{% for product in product_list %}', '\n    <li>', 
         '{{ product.name }}', ': ', '{{ product.price|format_price }}', 
         '</li>\n', 
         '{% endfor %}', 
         '\n\n</ul>\n']
        """
        """             ?s可以匹配行起始符"""
        tokens = re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)

        for token in tokens:
            if token.startswith('{#'):
                # Commnet: ignore it and move on
                continue
            elif token.startswith('{{'):
                # An expressiono to evalute.
                # 处理 {{ }}tag块
                expr = self._expr_code(token[2:-2].strip())
                buffered.append("to_str(%s)" % expr)
            elif token.startswith('{%'):
                # Action tag: split into words and parse further.
                # 处理 {{% %}}块
                flush_output()
                words = token[2:-2].strip().split()
                if words[0] == 'if':
                    # An if statement: evaluate the expression to determine if.
                    if len(words) != 2:
                        self._syntax_error("Don't understand if", token)
                    ops_stack.append('if')
                    code.add_line("if %s:" % self._expr_code(words[1]))
                    code.indent()
                elif words[0] == 'for':
                    # A loop: iterate over expression result.
                    #if len(words) != 4 or words[2] != 'in':
                    #    self._syntax_error("Don't understand for", token)
                    ops_stack.append('for')
                    # 重新划分块区
                    for_blocks = re.split(r"(?s)(for|in)", token[2:-2].strip())
                    # 取出for的循环变量
                    loop_vars = for_blocks[2].strip().split(",")
                    # 放置局部变量
                    for var in loop_vars:
                        self._variable(var.strip(), self.loop_vars)

                    aux = map(lambda x: "c_%s" % x.strip(), loop_vars)
                    new_loop_vars_block = ",".join(aux)
                    code.add_line(
                        "for %s in %s:" % (
                            new_loop_vars_block,
                            self._expr_code(for_blocks[4].strip())
                        )
                    )
                    '''
                    self._variable(words[1], self.loop_vars)
                    code.add_line(
                        "for c_%s in %s:" % (
                            words[1],
                            self._expr_code(words[3])
                        )
                    )
                    '''
                    code.indent()
                elif words[0].startswith('end'):
                    # Endsomething.  Pop the ops stack.
                    if len(words) != 1:
                        self._syntax_error("Don't understand end", token)
                    end_what = words[0][3:]
                    if not ops_stack:
                        self._syntax_error("Too many ends", token)
                    start_what = ops_stack.pop()
                    if start_what != end_what:
                        self._syntax_error("Mismatched end tag", end_what)
                    code.dedent()
                else:
                    self._syntax_error("Don't understand tag", words[0])
            else:
                # Literal content.  If it isn't empty, output it.
                # 处理字面量,将所有字面转换成
                # extend_result(['\n<p>Welcome, ', to_str(c_user_name))这种代码
                token = token.strip(" ")
                if token == '\n':
                    continue
                #if token:
                    #if token.startswith('\n'):
                    #    buffered.append(repr(token[1:]))
                    #else:
                    #    buffered.append(repr(token))
                if token:
                    buffered.append(repr(token))

        if ops_stack:
            self._syntax_error("Unmatched action tag", ops_stack[-1])

        flush_output()
        # 差集处理所有的全局变量，并把变量复制放在预留好的CodeBuilder对象子区
        for var_name in self.all_vars - self.loop_vars:
            vars_code.add_line("c_%s = context[%r]" % (var_name, var_name))

        code.add_line("return ''.join(result)")
        code.dedent()
        # 生成的代码可以直接调用了
        # print(code)
        self._render_function = code.get_globals()['render_function']

    def _expr_code(self, expr):
        """Generate a Python expression for `expr`."""
        if "|" in expr:
        # Var | base64 | print --> c_print(c_base64(_expr_code(Var)))
            pipes = expr.split("|")
            code = self._expr_code(pipes[0])
            for func in pipes[1:]:
                self._variable(func, self.all_vars)
                code = "c_%s(%s)" % (func, code)
        elif "." in expr:
        # Var.a.b.c --> do_dots(_expr_code(Var), a, b, c)
            dots = expr.split(".")
            code = self._expr_code(dots[0])
            args = ", ".join(repr(d) for d in dots[1:])
            code = "do_dots(%s, %s)" % (code, args)
        else:
        # Var --> c_Var
            self._variable(expr, self.all_vars)
            code = "c_%s" % expr
        return code

    def _variable(self, name, vars_set):
        """Track that `name` is used as a variable.
        Adds the name to `vars_set`, a set of variable names.
        Raises an syntax error if `name` is not a valid name.
        """
        if not re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", name):
            self._syntax_error("Not a valid name", name)
        vars_set.add(name)

    def render(self, context=None):
        """Render this template by applying it to `context`.

        `context` is a dictionary of values to use in this rendering.

        """
        # Make the complete context we'll use.
        render_context = dict(self.context)
        if context:
            render_context.update(context)
        return self._render_function(render_context, self._do_dots)

    def _do_dots(self, value, *dots):
        """a.b.c --> _do_dots(a, b, c)"""
        """Evaluate dotted expressions at runtime."""
        for dot in dots:
            try:
                value = getattr(value, dot)
            except AttributeError:
                value = value[dot]
            if callable(value):
                value = value()
        return value

    def _syntax_error(self, msg, thing):
        """Raise a syntax error using `msg`, and showing `thing`."""
        #raise TempliteSyntaxError("%s: %r" % (msg, thing))
        raise Exception("error")

code = CodeBuilder()
code.add_line("def render_function(context, do_dots):")
code.indent()
vars_code = code.add_section()
code.add_line("result=[]")
code.add_line("append_result = result.append")
code.add_line("extend_result = result.extend")
code.add_line("to_str = str")
buffered = []


def flush_output():
    """Force `buffered` to the code builder"""
    if len(buffered) == 1:
        code.add_line("append_result(%s)" % buffered[0])
    elif len(buffered) > 1:
        code.add_line("extend_result([%s])" % ", ".join(buffered))
    del buffered[:]


tests = '''
<p>Welcome, {{user_name}}!</p>
<p>Products:</p>
<ul>
{% for product in product_list %}
    <li>{{ product.name }}: {{ product.price|format_price }}</li>
{% endfor %}
{% for product in product_list %}
    {% for key, value in product.item|items %}
    <li>{{ key }}: {{ value }}</li>
    {% endfor %}
{% endfor %}
</ul>
'''

class product:
    def __init__(self, name, price, item):
        self.name = name
        self.price = price
        self.item = item

l = [product("sad", 12, {"da": 23}), product('coco', 324, {'gg':67})]

def format_price(price):
    return "%s" % price

def items(item):
    return item.items()

T = Templite(tests, {'user_name':"taotao", 'product_list':l, 'format_price':format_price, 'items':items})

print(T.render())

